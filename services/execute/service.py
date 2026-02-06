"""
Execute Service - Executes plans by commanding effectors.
Listens to: PLAN_RESULT
Publishes to: EXECUTE_RESULT, environment commands, knowledge updates
"""
import sys
import time

sys.path.insert(0, '/app')
from shared.mqtt_client import MQTTClient, Topics

# Cached state
knowledge = None
grid = None

OBSTACLE = 1


def handle_knowledge_update(payload):
    global knowledge
    knowledge = payload


def handle_environment_update(payload):
    global grid
    grid = payload.get('grid', {})


def handle_plan_result(payload):
    """Execute the plan."""
    action = payload.get('action')
    details = payload.get('details')
    
    if action == 'continue':
        execute_continue()
    elif action == 'start_mission':
        execute_start_mission(details)
    elif action == 'replan':
        execute_replan(details)
    elif action == 'deliver':
        execute_delivery(details)
    elif action == 'end_mission':
        execute_end_mission()
    elif action == 'wait':
        execute_wait(details)
    else:
        print(f"[Execute] Unknown action: {action}")


def execute_continue():
    """Move robot to next position in plan."""
    global knowledge, grid
    
    if not knowledge:
        return
    
    if knowledge.get('is_stuck'):
        print("[Execute] Robot is stuck, waiting")
        return
    
    plan = knowledge.get('current_plan')
    if not plan:
        return
    
    idx = knowledge.get('current_plan_index', 0)
    if idx >= len(plan):
        return
    
    next_pos = plan[idx]
    
    # Check if valid
    if grid:
        row, col = next_pos[0], next_pos[1]
        if grid.get('grid', [[]])[row][col] == OBSTACLE:
            return
        if next_pos in grid.get('dynamic_obstacles', []):
            return
    
    # Command robot to move
    client.publish('environment/move_robot', {'position': next_pos})
    
    # Update knowledge
    base = knowledge.get('base_location', [1, 1])
    client.publish('knowledge/set', {
        'robot_position': next_pos,
        'robot_is_at_base': (next_pos == base),
        'current_plan_index': idx + 1,
        'total_distance_traveled': knowledge.get('total_distance_traveled', 0) + 1
    })
    
    print(f"[Execute] Moved to {next_pos}")
    client.publish(Topics.EXECUTE_RESULT, {'status': 'moved', 'position': next_pos})


def execute_start_mission(details):
    """Start new delivery mission."""
    global knowledge
    
    orders = details['orders_to_load']
    sequence = details['delivery_sequence']
    path = details['full_path']
    
    # Load orders onto robot
    for order in orders:
        client.publish('environment/load_order', {'order': order})
    
    # Update knowledge
    loaded_ids = {o['order_id'] for o in orders}
    pending = [o for o in knowledge.get('pending_orders', []) if o['order_id'] not in loaded_ids]
    
    client.publish('knowledge/set', {
        'pending_orders': pending,
        'loaded_orders': orders,
        'current_plan': path,
        'current_plan_index': 0,
        'delivery_sequence': sequence,
        'original_last_delivery': sequence[-1] if sequence else None,
        'mission_in_progress': True,
        'last_mission_start_time': time.time(),
        'is_stuck': False
    })
    
    print(f"[Execute] Started mission with {len(orders)} orders")
    client.publish(Topics.EXECUTE_RESULT, {'status': 'mission_started', 'orders': len(orders)})


def execute_replan(details):
    """Apply new plan."""
    global knowledge
    
    new_path = details['new_path']
    new_sequence = details.get('new_sequence', [])
    
    updates = {
        'is_stuck': False,
        'current_plan': new_path,
        'current_plan_index': 0,
        'number_of_replans': knowledge.get('number_of_replans', 0) + 1
    }
    
    if new_sequence:
        updates['delivery_sequence'] = new_sequence
    
    client.publish('knowledge/set', updates)
    
    print(f"[Execute] Replanned, path length: {len(new_path)}")
    client.publish(Topics.EXECUTE_RESULT, {'status': 'replanned'})


def execute_delivery(details):
    """Deliver order at current location."""
    global knowledge
    
    order = details['order']
    order_id = order['order_id']
    delivery_loc = order['delivery_location']
    
    # Command robot to deliver
    client.publish('environment/deliver_order', {'order_id': order_id})
    
    # Update knowledge
    delivery_time = time.time() - order['timestamp']
    loaded = [o for o in knowledge.get('loaded_orders', []) if o['order_id'] != order_id]
    completed = knowledge.get('completed_orders', []) + [order]
    times = knowledge.get('delivery_times', []) + [delivery_time]
    sequence = knowledge.get('delivery_sequence', [])
    if delivery_loc in sequence:
        sequence = [s for s in sequence if s != delivery_loc]
    
    client.publish('knowledge/set', {
        'loaded_orders': loaded,
        'completed_orders': completed,
        'delivery_times': times,
        'delivery_sequence': sequence
    })
    
    print(f"[Execute] Delivered {order_id}")
    client.publish(Topics.EXECUTE_RESULT, {'status': 'delivered', 'order_id': order_id})


def execute_end_mission():
    """End current mission."""
    client.publish('environment/clear_orders', {})
    
    client.publish('knowledge/set', {
        'mission_in_progress': False,
        'current_plan': None,
        'current_plan_index': 0,
        'delivery_sequence': [],
        'original_last_delivery': None,
        'loaded_orders': [],
        'is_stuck': False
    })
    
    print("[Execute] Mission ended")
    client.publish(Topics.EXECUTE_RESULT, {'status': 'mission_ended'})


def execute_wait(details):
    """Robot waits (stuck)."""
    reason = details.get('reason', 'unknown')
    
    client.publish('knowledge/set', {'is_stuck': True})
    
    print(f"[Execute] Waiting: {reason}")
    client.publish(Topics.EXECUTE_RESULT, {'status': 'waiting', 'reason': reason})


if __name__ == '__main__':
    print("[Execute] Service starting...")
    
    client = MQTTClient('execute-service')
    client.connect()
    
    # Subscribe to state updates
    client.subscribe(Topics.KNOWLEDGE_UPDATE, handle_knowledge_update)
    client.subscribe(Topics.ENVIRONMENT_UPDATE, handle_environment_update)
    
    # Subscribe to plan results
    client.subscribe(Topics.PLAN_RESULT, handle_plan_result)
    
    print("[Execute] Service ready, waiting for messages...")
    client.loop_forever()