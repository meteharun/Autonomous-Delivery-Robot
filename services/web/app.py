from flask import Flask, render_template, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import sys
import os
import time

# Monkey patch for eventlet - MUST be at the top
import eventlet
eventlet.monkey_patch()

from environment.grid_world import GridWorld
from environment.robot import Robot, Order
from mape_k.knowledge import Knowledge
from mape_k.monitor import Monitor
from mape_k.analyze import Analyze
from mape_k.plan import Plan
from mape_k.execute import Execute

app = Flask(__name__)
app.config['SECRET_KEY'] = 'delivery-robot-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global system instance
system = None
running = False


class WebDeliverySystem:
    """Delivery system adapted for web visualization."""
    
    def __init__(self):
        # Initialize environment (Managed Resources)
        self.grid_world = GridWorld(width=22, height=15)
        base_location = self.grid_world.base_location
        
        # Initialize robot (Managed Resource)
        self.robot = Robot(start_position=base_location, max_capacity=3)
        
        # Initialize Knowledge Base (pure storage, no environment references)
        self.knowledge = Knowledge(base_location, max_capacity=3)
        
        # Initialize MAPE components
        # Monitor: reads from environment, writes to knowledge
        self.monitor = Monitor(self.knowledge, self.grid_world, self.robot)
        
        # Analyze: reads from knowledge only
        self.analyze = Analyze(self.knowledge)
        
        # Plan: reads from knowledge, uses grid_world for pathfinding
        self.plan = Plan(self.knowledge, self.grid_world)
        
        # Execute: reads plan, commands environment, updates knowledge
        self.execute = Execute(self.knowledge, self.grid_world, self.robot)
        
        # Simulation control
        self.step_delay = 0.4
        self.order_counter = 0
    
    def add_order(self, row, col):
        """Add a delivery order at the specified location."""
        delivery_location = (row, col)
        
        if delivery_location not in self.grid_world.delivery_locations:
            return False
        
        self.order_counter += 1
        order_id = f"ORD_{self.order_counter:03d}"
        
        order = Order(
            order_id=order_id,
            delivery_location=delivery_location,
            timestamp=time.time()
        )
        
        self.knowledge.add_order(order)
        print(f"Order created: {order_id} -> {delivery_location}")
        return True
    
    def toggle_obstacle(self, row, col):
        """Toggle dynamic obstacle at the specified location."""
        pos = (row, col)
        
        if row <= 1 and col <= 1:
            return False
        if pos in self.grid_world.delivery_locations:
            return False
        if self.grid_world.grid[row, col] == self.grid_world.OBSTACLE:
            return False
        if pos == self.robot.get_position():
            return False
        
        if pos in self.grid_world.dynamic_obstacles:
            self.grid_world.remove_dynamic_obstacle(pos)
            print(f"Removed obstacle at {pos}")
        else:
            self.grid_world.add_dynamic_obstacle(pos)
            print(f"Added obstacle at {pos}")
        
        return True
    
    def mape_loop_iteration(self):
        """Execute one iteration of the MAPE-K loop."""
        # MONITOR: Read from environment, write to knowledge
        monitoring_results = self.monitor.monitor_step()
        
        # ANALYZE: Read from knowledge, decide what to do
        analysis = self.analyze.analyze_situation(monitoring_results)
        
        # PLAN: Create adaptation plan using knowledge and grid_world
        if analysis['requires_adaptation']:
            adaptation_plan = self.plan.create_plan(analysis)
        else:
            adaptation_plan = {'action': 'continue', 'details': None}
        
        # EXECUTE: Command environment, update knowledge
        self.execute.execute_plan(adaptation_plan)
        
        return analysis
    
    def get_state(self):
        """Get the current state for visualization."""
        pending_locations = [list(order.delivery_location) for order in self.knowledge.pending_orders]
        
        delivery_sequence = {}
        for idx, loc in enumerate(self.knowledge.delivery_sequence):
            delivery_sequence[f"{loc[0]},{loc[1]}"] = idx + 1
        
        last_delivery_location = None
        if self.knowledge.delivery_sequence:
            last_loc = self.knowledge.delivery_sequence[-1]
            last_delivery_location = list(last_loc)
        elif self.knowledge.original_last_delivery:
            last_delivery_location = list(self.knowledge.original_last_delivery)
        
        countdown = "-"
        if self.knowledge.pending_orders:
            time_elapsed = time.time() - self.knowledge.last_mission_start_time
            time_remaining = self.knowledge.mission_timeout - time_elapsed
            if time_remaining > 0:
                minutes = int(time_remaining // 60)
                seconds = int(time_remaining % 60)
                countdown = f"{minutes:02d}:{seconds:02d}"
            else:
                if self.knowledge.mission_in_progress:
                    countdown = "Waiting..."
                else:
                    countdown = "Starting..."
        
        return {
            'grid': self.grid_world.grid.tolist(),
            'width': self.grid_world.width,
            'height': self.grid_world.height,
            'robot_position': list(self.robot.get_position()),
            'base_location': list(self.grid_world.base_location),
            'delivery_locations': [list(loc) for loc in self.grid_world.delivery_locations],
            'dynamic_obstacles': [list(loc) for loc in self.grid_world.dynamic_obstacles],
            'pending_locations': pending_locations,
            'delivery_sequence': delivery_sequence,
            'last_delivery_location': last_delivery_location,
            'current_path': [list(loc) for loc in (self.knowledge.current_plan or [])],
            'current_path_index': self.knowledge.current_plan_index,
            'loaded_orders': len(self.knowledge.loaded_orders),
            'pending_count': len(self.knowledge.pending_orders),
            'is_stuck': self.knowledge.is_stuck,
            'countdown': countdown,
            'mission_in_progress': self.knowledge.mission_in_progress,
            'metrics': self.knowledge.get_metrics()
        }


def simulation_loop():
    """Background greenlet running the simulation."""
    global system, running
    
    while True:
        if running and system:
            system.mape_loop_iteration()
            state = system.get_state()
            socketio.emit('state_update', state)
            for _ in range(8):
                eventlet.sleep(0.05)
        else:
            eventlet.sleep(0.05)


click_queue = []
click_queue_lock = eventlet.semaphore.Semaphore()


def process_click_queue():
    """Background greenlet to process clicks immediately."""
    global system, click_queue
    
    while True:
        click_to_process = None
        with click_queue_lock:
            if click_queue and system:
                click_to_process = click_queue.pop(0)
        
        if click_to_process:
            row, col = click_to_process['row'], click_to_process['col']
            
            if (row, col) in system.grid_world.delivery_locations:
                system.add_order(row, col)
            else:
                system.toggle_obstacle(row, col)
            
            state = system.get_state()
            socketio.emit('state_update', state)
        
        eventlet.sleep(0.01)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('/app/assets', filename)


@app.route('/api/state')
def get_state():
    if system:
        return jsonify(system.get_state())
    return jsonify({'error': 'System not initialized'})


@socketio.on('connect')
def handle_connect():
    print('Client connected')
    if system:
        emit('state_update', system.get_state())


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('click')
def handle_click(data):
    """Handle click events from the web client."""
    global system, click_queue
    
    if not system:
        return
    
    row = data.get('row')
    col = data.get('col')
    
    if row is None or col is None:
        return
    
    print(f"Click received: row={row}, col={col}")
    
    with click_queue_lock:
        click_queue.append({'row': row, 'col': col})


@socketio.on('reset')
def handle_reset():
    """Reset the simulation."""
    global system
    
    system = WebDeliverySystem()
    print("Simulation reset")
    socketio.emit('state_update', system.get_state())


if __name__ == '__main__':
    system = WebDeliverySystem()
    running = True
    
    eventlet.spawn(simulation_loop)
    eventlet.spawn(process_click_queue)
    
    print("=" * 50)
    print("Starting Autonomous Delivery Robot Web Server")
    print("Open http://localhost:5000 in your browser")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)