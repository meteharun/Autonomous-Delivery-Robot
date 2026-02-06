"""
Web Service - Serves UI and triggers MAPE-K loop via MQTT.
"""
from flask import Flask, render_template, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import time
import os
import json

import eventlet
eventlet.monkey_patch()

import paho.mqtt.client as mqtt

app = Flask(__name__)
app.config['SECRET_KEY'] = 'delivery-robot-secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

MQTT_BROKER = os.environ.get('MQTT_BROKER', 'mqtt')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))

# Topics
class Topics:
    SYSTEM_INIT = 'system/init'
    SYSTEM_RESET = 'system/reset'
    USER_ADD_ORDER = 'user/add_order'
    USER_TOGGLE_OBSTACLE = 'user/toggle_obstacle'
    MONITOR_REQUEST = 'mape/monitor/request'
    KNOWLEDGE_UPDATE = 'knowledge/update'
    ENVIRONMENT_UPDATE = 'environment/update'
    STATE_UPDATE = 'state/update'

# State
mqtt_client = None
running = False
order_counter = 0
current_knowledge = None
current_environment = None


def on_mqtt_connect(client, userdata, flags, rc):
    print(f"[Web] Connected to MQTT broker with code {rc}")
    client.subscribe(Topics.KNOWLEDGE_UPDATE)
    client.subscribe(Topics.ENVIRONMENT_UPDATE)
    client.subscribe(Topics.STATE_UPDATE)


def on_mqtt_message(client, userdata, msg):
    global current_knowledge, current_environment
    
    try:
        payload = json.loads(msg.payload.decode())
    except:
        return
    
    if msg.topic == Topics.KNOWLEDGE_UPDATE:
        if current_knowledge:
            current_knowledge.update(payload)
        else:
            current_knowledge = payload
        broadcast_state()
    
    elif msg.topic == Topics.ENVIRONMENT_UPDATE:
        current_environment = payload
        broadcast_state()


def broadcast_state():
    """Broadcast current state to web clients."""
    global current_knowledge, current_environment
    
    if not current_knowledge or not current_environment:
        return
    
    grid = current_environment.get('grid', {})
    robot = current_environment.get('robot', {})
    knowledge = current_knowledge
    
    pending_locations = [o['delivery_location'] for o in knowledge.get('pending_orders', [])]
    
    delivery_sequence = {}
    for idx, loc in enumerate(knowledge.get('delivery_sequence', [])):
        key = f"{loc[0]},{loc[1]}"
        delivery_sequence[key] = idx + 1
    
    last_delivery = knowledge.get('delivery_sequence', [])
    last_delivery_location = last_delivery[-1] if last_delivery else knowledge.get('original_last_delivery')
    
    countdown = "-"
    if knowledge.get('pending_orders'):
        elapsed = time.time() - knowledge.get('last_mission_start_time', time.time())
        remaining = knowledge.get('mission_timeout', 30) - elapsed
        if remaining > 0:
            countdown = f"{int(remaining // 60):02d}:{int(remaining % 60):02d}"
        else:
            countdown = "Starting..." if not knowledge.get('mission_in_progress') else "Waiting..."
    
    times = knowledge.get('delivery_times', [])
    avg_time = sum(times) / len(times) if times else 0
    
    state = {
        'grid': grid.get('grid', []),
        'width': grid.get('width', 22),
        'height': grid.get('height', 15),
        'robot_position': robot.get('position', [1, 1]),
        'base_location': grid.get('base_location', [1, 1]),
        'delivery_locations': grid.get('delivery_locations', []),
        'dynamic_obstacles': grid.get('dynamic_obstacles', []),
        'pending_locations': pending_locations,
        'delivery_sequence': delivery_sequence,
        'last_delivery_location': last_delivery_location,
        'current_path': knowledge.get('current_plan') or [],
        'current_path_index': knowledge.get('current_plan_index', 0),
        'loaded_orders': len(knowledge.get('loaded_orders', [])),
        'pending_count': len(knowledge.get('pending_orders', [])),
        'is_stuck': knowledge.get('is_stuck', False),
        'countdown': countdown,
        'mission_in_progress': knowledge.get('mission_in_progress', False),
        'metrics': {
            'total_deliveries': len(knowledge.get('completed_orders', [])),
            'pending_orders': len(knowledge.get('pending_orders', [])),
            'total_distance': knowledge.get('total_distance_traveled', 0),
            'replans': knowledge.get('number_of_replans', 0),
            'avg_delivery_time': avg_time
        }
    }
    
    socketio.emit('state_update', state)


def connect_mqtt():
    global mqtt_client
    
    mqtt_client = mqtt.Client(client_id='web-service')
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    
    for i in range(30):
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            mqtt_client.loop_start()
            time.sleep(1)
            print("[Web] Connected to MQTT")
            return
        except Exception as e:
            print(f"[Web] MQTT connection attempt {i+1} failed: {e}")
            time.sleep(2)
    
    raise Exception("Could not connect to MQTT broker")


def init_system():
    """Send init message to all services."""
    mqtt_client.publish(Topics.SYSTEM_INIT, json.dumps({
        'base_location': [1, 1],
        'max_capacity': 3
    }))
    print("[Web] System initialized")
    time.sleep(1)


def mape_loop():
    """Continuously trigger MAPE-K loop."""
    global running
    
    while True:
        if running:
            mqtt_client.publish(Topics.MONITOR_REQUEST, json.dumps({}))
            eventlet.sleep(0.4)
        else:
            eventlet.sleep(0.1)


# ==================== ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('/app/assets', filename)


@app.route('/api/state')
def api_state():
    return jsonify({'status': 'ok'})


# ==================== SOCKET EVENTS ====================

@socketio.on('connect')
def handle_connect():
    print('[Web] Client connected')
    broadcast_state()


@socketio.on('disconnect')
def handle_disconnect():
    print('[Web] Client disconnected')


@socketio.on('click')
def handle_click(data):
    global order_counter, current_environment
    
    row = data.get('row')
    col = data.get('col')
    
    if row is None or col is None:
        return
    
    print(f"[Web] Click: ({row}, {col})")
    
    if current_environment:
        grid = current_environment.get('grid', {})
        if [row, col] in grid.get('delivery_locations', []):
            order_counter += 1
            order_id = f"ORD_{order_counter:03d}"
            mqtt_client.publish(Topics.USER_ADD_ORDER, json.dumps({
                'order_id': order_id,
                'delivery_location': [row, col],
                'timestamp': time.time()
            }))
            print(f"[Web] Added order {order_id}")
        else:
            mqtt_client.publish(Topics.USER_TOGGLE_OBSTACLE, json.dumps({
                'position': [row, col]
            }))


@socketio.on('reset')
def handle_reset():
    global order_counter, current_knowledge, current_environment
    
    order_counter = 0
    current_knowledge = None
    current_environment = None
    
    mqtt_client.publish(Topics.SYSTEM_RESET, json.dumps({
        'base_location': [1, 1],
        'max_capacity': 3
    }))
    print("[Web] System reset")


# ==================== MAIN ====================

if __name__ == '__main__':
    print("[Web] Service starting...")
    
    connect_mqtt()
    init_system()
    
    running = True
    eventlet.spawn(mape_loop)
    
    print("=" * 50)
    print("Autonomous Delivery Robot - MQTT Architecture")
    print("Open http://localhost:5000 in your browser")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)