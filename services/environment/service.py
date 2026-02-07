"""
Environment Service - Manages Grid and Robot state.
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
BASE = 2
DELIVERY = 3

# State
grid = None
robot = None
client = None


def create_initial_grid():
    width = CONFIG['grid']['width']
    height = CONFIG['grid']['height']
    g = [[0 for _ in range(width)] for _ in range(height)]
    
    base_location = CONFIG['robot']['base_location']
    for r in range(2):
        for c in range(2):
            g[r][c] = BASE
    
    delivery_locations = [
        [4, 4], [8, 2], [12, 4], [2, 10], [6, 12], [10, 10], [13, 12],
        [0, 15], [14, 2], [14, 18], [3, 19], [11, 20]
    ]
    for loc in delivery_locations:
        if 0 <= loc[0] < height and 0 <= loc[1] < width:
            g[loc[0]][loc[1]] = DELIVERY
    
    obstacles = [
        [4, 0], [5, 0], [0, 3], [0, 4], [2, 3], [3, 3], [5, 2], [6, 2],
        [2, 6], [3, 6], [6, 5], [7, 5], [7, 6], [9, 1], [10, 1], [10, 2],
        [9, 4], [9, 5], [12, 1], [13, 1], [11, 6], [12, 6], [5, 7], [6, 7],
        [14, 4], [14, 5], [0, 9], [1, 9], [3, 9], [4, 9], [0, 13], [1, 13],
        [3, 13], [4, 13], [7, 9], [8, 9], [7, 14], [8, 14], [5, 10], [5, 11],
        [9, 12], [9, 13], [11, 8], [12, 8], [11, 14], [12, 14], [14, 9], [14, 10],
        [14, 13], [14, 14], [6, 15], [6, 16], [10, 15], [10, 16], [0, 17], [1, 17],
        [0, 21], [1, 21], [2, 17], [2, 18], [4, 20], [4, 21], [6, 18], [6, 19],
        [8, 17], [9, 17], [8, 21], [9, 21], [12, 17], [12, 18], [12, 20], [12, 21],
    ]
    for pos in obstacles:
        if 0 <= pos[0] < height and 0 <= pos[1] < width and g[pos[0]][pos[1]] == 0:
            g[pos[0]][pos[1]] = OBSTACLE
    
    return {
        'width': width,
        'height': height,
        'grid': g,
        'base_location': base_location,
        'delivery_locations': delivery_locations,
        'dynamic_obstacles': []
    }


def create_initial_robot():
    return {
        'position': list(CONFIG['robot']['base_location']),
        'loaded_orders': [],
        'is_at_base': True
    }


def publish_state():
    global grid, robot, client
    if grid and robot:
        client.publish(TOPICS['environment_update'], json.dumps({
            'grid': grid,
            'robot': robot
        }))


def handle_message(client_obj, userdata, msg):
    global grid, robot
    
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8')) if msg.payload else {}
        
        if topic == TOPICS['system_init']:
            grid = create_initial_grid()
            robot = create_initial_robot()
            print("[Environment] Initialized")
            publish_state()
        
        elif topic == TOPICS['system_reset']:
            grid = create_initial_grid()
            robot = create_initial_robot()
            print("[Environment] Reset")
            publish_state()
        
        elif topic == TOPICS['user_toggle_obstacle']:
            if not grid:
                return
            pos = payload.get('position')
            row, col = pos[0], pos[1]
            
            if pos in grid['dynamic_obstacles']:
                grid['dynamic_obstacles'].remove(pos)
                print(f"[Environment] Removed obstacle {pos}")
            else:
                if row <= 1 and col <= 1:
                    return
                if pos in grid['delivery_locations']:
                    return
                if grid['grid'][row][col] == OBSTACLE:
                    return
                if robot and pos == robot['position']:
                    return
                grid['dynamic_obstacles'].append(pos)
                print(f"[Environment] Added obstacle {pos}")
            publish_state()
        
        elif topic == TOPICS['environment_move']:
            if not robot:
                return
            robot['position'] = payload['position']
            base = CONFIG['robot']['base_location']
            robot['is_at_base'] = (robot['position'] == base)
            publish_state()
        
        elif topic == TOPICS['environment_load']:
            if not robot:
                return
            robot['loaded_orders'].append(payload['order'])
            publish_state()
        
        elif topic == TOPICS['environment_deliver']:
            if not robot:
                return
            order_id = payload['order_id']
            robot['loaded_orders'] = [o for o in robot['loaded_orders'] if o['order_id'] != order_id]
            publish_state()
        
        elif topic == TOPICS['environment_clear']:
            if not robot:
                return
            robot['loaded_orders'] = []
            publish_state()
    
    except Exception as e:
        print(f"[Environment] Error: {e}")


def on_connect(client_obj, userdata, flags, rc):
    print("[Environment] Connected to MQTT")
    client_obj.subscribe(TOPICS['system_init'])
    client_obj.subscribe(TOPICS['system_reset'])
    client_obj.subscribe(TOPICS['user_toggle_obstacle'])
    client_obj.subscribe(TOPICS['environment_move'])
    client_obj.subscribe(TOPICS['environment_load'])
    client_obj.subscribe(TOPICS['environment_deliver'])
    client_obj.subscribe(TOPICS['environment_clear'])


if __name__ == '__main__':
    print("[Environment] Starting...")
    
    client = mqtt.Client(client_id=f"environment-{uuid.uuid4().hex[:8]}")
    client.on_connect = on_connect
    client.on_message = handle_message
    
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            break
        except:
            print("[Environment] Waiting for MQTT...")
            time.sleep(2)
    
    print("[Environment] Ready")
    client.loop_forever()