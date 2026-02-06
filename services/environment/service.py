"""
Environment Service - Manages Grid and Robot state via MQTT.
Listens for commands and publishes state updates.
"""
import sys

sys.path.insert(0, '/app')
from shared.mqtt_client import MQTTClient, Topics
from shared.state_models import create_initial_grid, create_initial_robot

# In-memory state
grid = None
robot = None

# Cell types
EMPTY = 0
OBSTACLE = 1
BASE = 2
DELIVERY_LOCATION = 3


def handle_init(payload):
    """Initialize environment state."""
    global grid, robot
    grid = create_initial_grid(22, 15)
    robot = create_initial_robot(tuple(grid['base_location']), 3)
    print(f"[Environment] Initialized grid {grid['width']}x{grid['height']}, robot at {robot['position']}")
    publish_state()


def handle_reset(payload):
    """Reset environment state."""
    handle_init(payload)


def handle_toggle_obstacle(payload):
    """Toggle dynamic obstacle."""
    global grid, robot
    if grid is None:
        return
    
    pos = payload.get('position')
    row, col = pos[0], pos[1]
    
    # Check if already a dynamic obstacle
    if pos in grid['dynamic_obstacles']:
        grid['dynamic_obstacles'].remove(pos)
        print(f"[Environment] Removed obstacle at {pos}")
        publish_state()
        return
    
    # Validation
    if not (0 <= row < grid['height'] and 0 <= col < grid['width']):
        return
    if row <= 1 and col <= 1:  # Base area
        return
    if pos in grid['delivery_locations']:
        return
    if grid['grid'][row][col] == OBSTACLE:
        return
    if robot and pos == robot['position']:
        return
    
    # Add obstacle
    grid['dynamic_obstacles'].append(pos)
    print(f"[Environment] Added obstacle at {pos}")
    publish_state()


def handle_move_robot(payload):
    """Move robot to new position."""
    global grid, robot
    if robot is None or grid is None:
        return
    
    new_pos = payload.get('position')
    robot['position'] = new_pos
    robot['is_at_base'] = (new_pos == grid['base_location'])
    publish_state()


def handle_load_order(payload):
    """Load order onto robot."""
    global robot
    if robot is None:
        return
    
    order = payload.get('order')
    if len(robot['loaded_orders']) < robot['max_capacity']:
        robot['loaded_orders'].append(order)
        publish_state()


def handle_deliver_order(payload):
    """Deliver order (remove from robot)."""
    global robot
    if robot is None:
        return
    
    order_id = payload.get('order_id')
    robot['loaded_orders'] = [o for o in robot['loaded_orders'] if o['order_id'] != order_id]
    publish_state()


def handle_clear_orders(payload):
    """Clear all orders from robot."""
    global robot
    if robot is None:
        return
    
    robot['loaded_orders'] = []
    publish_state()


def publish_state():
    """Publish current environment state."""
    global grid, robot, client
    if grid and robot:
        client.publish(Topics.ENVIRONMENT_UPDATE, {
            'grid': grid,
            'robot': robot
        })


def handle_monitor_request(payload):
    """Provide environment state for monitor."""
    publish_state()


if __name__ == '__main__':
    print("[Environment] Service starting...")
    
    client = MQTTClient('environment-service')
    client.connect()
    
    # Subscribe to topics
    client.subscribe(Topics.SYSTEM_INIT, handle_init)
    client.subscribe(Topics.SYSTEM_RESET, handle_reset)
    client.subscribe(Topics.USER_TOGGLE_OBSTACLE, handle_toggle_obstacle)
    client.subscribe(Topics.MONITOR_REQUEST, handle_monitor_request)
    client.subscribe('environment/move_robot', handle_move_robot)
    client.subscribe('environment/load_order', handle_load_order)
    client.subscribe('environment/deliver_order', handle_deliver_order)
    client.subscribe('environment/clear_orders', handle_clear_orders)
    
    print("[Environment] Service ready, waiting for messages...")
    client.loop_forever()