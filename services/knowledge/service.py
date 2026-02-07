"""
Knowledge Service - Maintains system state.
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

# State
knowledge = None
client = None


def create_initial_knowledge():
    return {
        'base_location': CONFIG['robot']['base_location'],
        'max_capacity': CONFIG['robot']['max_capacity'],
        'mission_timeout': CONFIG['robot']['mission_timeout'],
        'robot_position': list(CONFIG['robot']['base_location']),
        'pending_orders': [],
        'loaded_orders': [],
        'completed_orders': [],
        'current_plan': None,
        'current_plan_index': 0,
        'delivery_sequence': [],
        'original_last_delivery': None,
        'mission_in_progress': False,
        'is_stuck': False,
        'last_mission_start_time': time.time(),
        'total_distance_traveled': 0,
        'number_of_replans': 0,
        'delivery_times': []
    }


def publish_state():
    global knowledge, client
    if knowledge:
        client.publish(TOPICS['knowledge_update'], json.dumps(knowledge))


def handle_message(client, userdata, msg):
    global knowledge
    
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8')) if msg.payload else {}
        
        if topic == TOPICS['system_init']:
            knowledge = create_initial_knowledge()
            print("[Knowledge] Initialized")
            publish_state()
        
        elif topic == TOPICS['system_reset']:
            knowledge = create_initial_knowledge()
            print("[Knowledge] Reset")
            publish_state()
        
        elif topic == TOPICS['user_add_order']:
            if not knowledge:
                return
            order = {
                'order_id': payload['order_id'],
                'delivery_location': payload['delivery_location'],
                'timestamp': payload.get('timestamp', time.time())
            }
            knowledge['pending_orders'].append(order)
            if len(knowledge['pending_orders']) == 1:
                knowledge['last_mission_start_time'] = time.time()
            print(f"[Knowledge] Added order {order['order_id']}")
            publish_state()
        
        elif topic == TOPICS['knowledge_set']:
            if not knowledge:
                return
            for key, value in payload.items():
                if key in knowledge:
                    knowledge[key] = value
            publish_state()
    
    except Exception as e:
        print(f"[Knowledge] Error: {e}")


def on_connect(client, userdata, flags, rc):
    print(f"[Knowledge] Connected to MQTT")
    client.subscribe(TOPICS['system_init'])
    client.subscribe(TOPICS['system_reset'])
    client.subscribe(TOPICS['user_add_order'])
    client.subscribe(TOPICS['knowledge_set'])


if __name__ == '__main__':
    print("[Knowledge] Starting...")
    
    client = mqtt.Client(client_id=f"knowledge-{uuid.uuid4().hex[:8]}")
    client.on_connect = on_connect
    client.on_message = handle_message
    
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            break
        except:
            print("[Knowledge] Waiting for MQTT...")
            time.sleep(2)
    
    print("[Knowledge] Ready")
    client.loop_forever()