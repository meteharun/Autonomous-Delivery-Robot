"""
Monitor Service - Reads sensors and publishes monitoring results.
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

# State cache
knowledge = None
environment = None
previous_obstacles = set()
client = None


def handle_message(client_obj, userdata, msg):
    global knowledge, environment, previous_obstacles
    
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8')) if msg.payload else {}
        
        if topic == TOPICS['knowledge_update']:
            knowledge = payload
        
        elif topic == TOPICS['environment_update']:
            environment = payload
        
        elif topic == TOPICS['system_reset']:
            previous_obstacles = set()
            knowledge = None
            environment = None
        
        elif topic == TOPICS['monitor_request']:
            if not knowledge or not environment:
                print("[Monitor] State not ready")
                return
            
            grid = environment.get('grid', {})
            robot = environment.get('robot', {})
            
            robot_position = robot.get('position', [1, 1])
            loaded_orders = robot.get('loaded_orders', [])
            is_at_base = robot.get('is_at_base', True)
            dynamic_obstacles = grid.get('dynamic_obstacles', [])
            
            # Check obstacle changes
            current_obstacles = set(tuple(o) for o in dynamic_obstacles)
            obstacle_removed = len(previous_obstacles - current_obstacles) > 0
            previous_obstacles = current_obstacles
            
            # Check path blocked
            path_blocked = False
            current_plan = knowledge.get('current_plan')
            plan_index = knowledge.get('current_plan_index', 0)
            
            if current_plan:
                for i in range(plan_index, len(current_plan)):
                    pos = current_plan[i]
                    grid_data = grid.get('grid', [])
                    if grid_data and grid_data[pos[0]][pos[1]] == 1:
                        path_blocked = True
                        break
                    if pos in dynamic_obstacles:
                        path_blocked = True
                        break
            
            # Check at delivery location
            at_delivery_location = False
            for order in loaded_orders:
                if order['delivery_location'] == robot_position:
                    at_delivery_location = True
                    break
            
            # Check mission start conditions
            needs_new_mission = False
            mission_in_progress = knowledge.get('mission_in_progress', False)
            pending_orders = knowledge.get('pending_orders', [])
            max_capacity = knowledge.get('max_capacity', 3)
            
            if not mission_in_progress:
                if len(pending_orders) >= max_capacity:
                    needs_new_mission = True
                elif pending_orders:
                    elapsed = time.time() - knowledge.get('last_mission_start_time', time.time())
                    if elapsed >= knowledge.get('mission_timeout', 30):
                        needs_new_mission = True
            
            # Publish results
            results = {
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
            
            client.publish(TOPICS['monitor_result'], json.dumps(results))
            print(f"[Monitor] Published: needs_mission={needs_new_mission}, blocked={path_blocked}")
    
    except Exception as e:
        print(f"[Monitor] Error: {e}")


def on_connect(client_obj, userdata, flags, rc):
    print("[Monitor] Connected to MQTT")
    client_obj.subscribe(TOPICS['knowledge_update'])
    client_obj.subscribe(TOPICS['environment_update'])
    client_obj.subscribe(TOPICS['monitor_request'])
    client_obj.subscribe(TOPICS['system_reset'])


if __name__ == '__main__':
    print("[Monitor] Starting...")
    
    client = mqtt.Client(client_id=f"monitor-{uuid.uuid4().hex[:8]}")
    client.on_connect = on_connect
    client.on_message = handle_message
    
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            break
        except:
            print("[Monitor] Waiting for MQTT...")
            time.sleep(2)
    
    print("[Monitor] Ready")
    client.loop_forever()