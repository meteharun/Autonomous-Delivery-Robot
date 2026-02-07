"""
Execute Service - Executes plans by commanding effectors.
"""
import paho.mqtt.client as mqtt
import json
import time
import uuid
import os

# Load config
with open('/app/config.json') as f:
    CONFIG = json.load(f)

BROKER = os.environ.get('MQTT_BROKER', CONFIG['mqtt']['broker'])
PORT = CONFIG['mqtt']['port']
TOPICS = CONFIG['topics']

OBSTACLE = 1

# State cache
knowledge = None
grid = None
client = None


def handle_message(client_obj, userdata, msg):
    global knowledge, grid, client
    
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8')) if msg.payload else {}
        
        if topic == TOPICS['knowledge_update']:
            knowledge = payload
        
        elif topic == TOPICS['environment_update']:
            grid = payload.get('grid', {})
        
        elif topic == TOPICS['plan_result']:
            action = payload.get('action')
            
            if action == 'continue':
                execute_continue()
            elif action == 'start_mission':
                execute_start(payload)
            elif action == 'replan':
                execute_replan(payload)
            elif action == 'deliver':
                execute_deliver(payload)
            elif action == 'end_mission':
                execute_end()
            elif action == 'wait':
                execute_wait(payload)
    
    except Exception as e:
        print(f"[Execute] Error: {e}")


def execute_continue():
    global knowledge, grid, client
    
    if not knowledge:
        return
    
    if knowledge.get('is_stuck'):
        return
    
    if not knowledge.get('mission_in_progress'):
        return
    
    plan = knowledge.get('current_plan')
    if not plan:
        return
    
    idx = knowledge.get('current_plan_index', 0)
    if idx >= len(plan):
        return
    
    next_pos = plan[idx]
    
    # Validate
    if grid:
        r, c = next_pos
        grid_data = grid.get('grid', [[]])
        if r < len(grid_data) and c < len(grid_data[0]):
            if grid_data[r][c] == OBSTACLE:
                return
        if next_pos in grid.get('dynamic_obstacles', []):
            return
    
    # Command Environment
    client.publish(TOPICS['environment_move'], json.dumps({'position': next_pos}))
    
    # Update Knowledge
    client.publish(TOPICS['knowledge_set'], json.dumps({
        'robot_position': next_pos,
        'current_plan_index': idx + 1,
        'total_distance_traveled': knowledge.get('total_distance_traveled', 0) + 1
    }))
    
    print(f"[Execute] Move to {next_pos}")


def execute_start(payload):
    global knowledge, client
    
    orders = payload['orders']
    sequence = payload['sequence']
    path = payload['path']
    
    # Load orders
    for order in orders:
        client.publish(TOPICS['environment_load'], json.dumps({'order': order}))
    
    # Update Knowledge - store original_last_delivery for path coloring
    loaded_ids = {o['order_id'] for o in orders}
    pending = [o for o in knowledge.get('pending_orders', []) if o['order_id'] not in loaded_ids]
    
    original_last = sequence[-1] if sequence else None
    
    client.publish(TOPICS['knowledge_set'], json.dumps({
        'pending_orders': pending,
        'loaded_orders': orders,
        'current_plan': path,
        'current_plan_index': 0,
        'delivery_sequence': sequence,
        'original_last_delivery': original_last,
        'mission_in_progress': True,
        'is_stuck': False,
        'last_mission_start_time': time.time()
    }))
    
    print(f"[Execute] Started mission: {len(orders)} orders")


def execute_replan(payload):
    global knowledge, client
    
    path = payload['path']
    sequence = payload.get('sequence', [])
    
    updates = {
        'current_plan': path,
        'current_plan_index': 0,
        'is_stuck': False,
        'number_of_replans': knowledge.get('number_of_replans', 0) + 1
    }
    if sequence:
        updates['delivery_sequence'] = sequence
    
    client.publish(TOPICS['knowledge_set'], json.dumps(updates))
    print(f"[Execute] Replanned: {len(path)} steps")


def execute_deliver(payload):
    global knowledge, client
    
    order = payload['order']
    order_id = order['order_id']
    loc = order['delivery_location']
    
    # Command Environment
    client.publish(TOPICS['environment_deliver'], json.dumps({'order_id': order_id}))
    
    # Update Knowledge
    delivery_time = time.time() - order['timestamp']
    loaded = [o for o in knowledge.get('loaded_orders', []) if o['order_id'] != order_id]
    completed = knowledge.get('completed_orders', []) + [order]
    times = knowledge.get('delivery_times', []) + [delivery_time]
    sequence = [s for s in knowledge.get('delivery_sequence', []) if s != loc]
    
    client.publish(TOPICS['knowledge_set'], json.dumps({
        'loaded_orders': loaded,
        'completed_orders': completed,
        'delivery_times': times,
        'delivery_sequence': sequence
    }))
    
    print(f"[Execute] Delivered {order_id}")


def execute_end():
    global client
    
    client.publish(TOPICS['environment_clear'], json.dumps({}))
    
    client.publish(TOPICS['knowledge_set'], json.dumps({
        'mission_in_progress': False,
        'current_plan': None,
        'current_plan_index': 0,
        'delivery_sequence': [],
        'original_last_delivery': None,
        'loaded_orders': [],
        'is_stuck': False
    }))
    
    print("[Execute] Mission ended")


def execute_wait(payload):
    global client
    client.publish(TOPICS['knowledge_set'], json.dumps({'is_stuck': True}))
    print(f"[Execute] Waiting: {payload.get('reason')}")


def on_connect(client_obj, userdata, flags, rc):
    print("[Execute] Connected to MQTT")
    client_obj.subscribe(TOPICS['knowledge_update'])
    client_obj.subscribe(TOPICS['environment_update'])
    client_obj.subscribe(TOPICS['plan_result'])


if __name__ == '__main__':
    print("[Execute] Starting...")
    
    client = mqtt.Client(client_id=f"execute-{uuid.uuid4().hex[:8]}")
    client.on_connect = on_connect
    client.on_message = handle_message
    
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            break
        except:
            print("[Execute] Waiting for MQTT...")
            time.sleep(2)
    
    print("[Execute] Ready")
    client.loop_forever()