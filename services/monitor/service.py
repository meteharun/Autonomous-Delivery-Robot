"""
Monitor Service - Reads sensors and publishes monitoring results.
Listens to: MONITOR_REQUEST
Publishes to: MONITOR_RESULT
"""
import sys
import time

sys.path.insert(0, '/app')
from shared.mqtt_client import MQTTClient, Topics

# Local state cache (updated via subscriptions)
knowledge = None
environment = None
previous_obstacles = set()


def handle_knowledge_update(payload):
    """Cache knowledge state."""
    global knowledge
    knowledge = payload


def handle_environment_update(payload):
    """Cache environment state."""
    global environment
    environment = payload


def handle_monitor_request(payload):
    """Execute monitoring step and publish results."""
    global knowledge, environment, previous_obstacles
    
    if not knowledge or not environment:
        print("[Monitor] State not ready, skipping")
        return
    
    grid = environment.get('grid', {})
    robot = environment.get('robot', {})
    
    # === SENSOR READINGS ===
    robot_position = robot.get('position', [1, 1])
    loaded_orders = robot.get('loaded_orders', [])
    is_at_base = robot.get('is_at_base', True)
    dynamic_obstacles = grid.get('dynamic_obstacles', [])
    
    # === CHECK CONDITIONS ===
    
    # Check if obstacle was removed
    current_obstacles = set(tuple(o) for o in dynamic_obstacles)
    prev_obstacles = previous_obstacles
    obstacle_removed = len(prev_obstacles - current_obstacles) > 0
    previous_obstacles = current_obstacles
    
    # Check if path is blocked
    path_blocked = False
    current_plan = knowledge.get('current_plan')
    current_plan_index = knowledge.get('current_plan_index', 0)
    
    if current_plan:
        for i in range(current_plan_index, len(current_plan)):
            pos = current_plan[i]
            grid_data = grid.get('grid', [])
            if grid_data and grid_data[pos[0]][pos[1]] == 1:  # OBSTACLE
                path_blocked = True
                break
            if pos in dynamic_obstacles:
                path_blocked = True
                break
    
    # Check if at delivery location
    at_delivery_location = False
    for order in loaded_orders:
        if order['delivery_location'] == robot_position:
            at_delivery_location = True
            break
    
    # Check if should start new mission
    needs_new_mission = False
    mission_in_progress = knowledge.get('mission_in_progress', False)
    pending_orders = knowledge.get('pending_orders', [])
    max_capacity = knowledge.get('max_capacity', 3)
    
    if not mission_in_progress:
        if len(pending_orders) >= max_capacity:
            needs_new_mission = True
        elif pending_orders:
            time_elapsed = time.time() - knowledge.get('last_mission_start_time', time.time())
            if time_elapsed >= knowledge.get('mission_timeout', 30):
                needs_new_mission = True
    
    # === BUILD AND PUBLISH RESULTS ===
    monitoring_results = {
        'sensor_data': {
            'robot_position': robot_position,
            'loaded_orders': loaded_orders,
            'is_at_base': is_at_base,
            'dynamic_obstacles': dynamic_obstacles,
            'mission_in_progress': mission_in_progress
        },
        'needs_new_mission': needs_new_mission,
        'path_blocked': path_blocked,
        'obstacle_removed': obstacle_removed,
        'at_delivery_location': at_delivery_location,
        'at_base': is_at_base,
        'knowledge': knowledge,
        'grid': grid
    }
    
    client.publish(Topics.MONITOR_RESULT, monitoring_results)
    print(f"[Monitor] Published results: needs_mission={needs_new_mission}, blocked={path_blocked}")


def handle_reset(payload):
    """Reset monitor state."""
    global previous_obstacles
    previous_obstacles = set()
    print("[Monitor] Reset")


if __name__ == '__main__':
    print("[Monitor] Service starting...")
    
    client = MQTTClient('monitor-service')
    client.connect()
    
    # Subscribe to state updates
    client.subscribe(Topics.KNOWLEDGE_UPDATE, handle_knowledge_update)
    client.subscribe(Topics.ENVIRONMENT_UPDATE, handle_environment_update)
    
    # Subscribe to commands
    client.subscribe(Topics.MONITOR_REQUEST, handle_monitor_request)
    client.subscribe(Topics.SYSTEM_RESET, handle_reset)
    
    print("[Monitor] Service ready, waiting for messages...")
    client.loop_forever()