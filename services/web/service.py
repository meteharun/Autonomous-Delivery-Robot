"""
Web Service - UI and MAPE-K loop trigger.
"""
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import json
import time
import os

import eventlet
eventlet.monkey_patch()

# Load config
with open('/app/config.json') as f:
    CONFIG = json.load(f)

BROKER = os.environ.get('MQTT_BROKER', CONFIG['mqtt']['broker'])
PORT = CONFIG['mqtt']['port']
TOPICS = CONFIG['topics']

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

mqtt_client = None
running = False
order_counter = 0
current_knowledge = None
current_environment = None


def on_mqtt_connect(client, userdata, flags, rc):
    print("[Web] Connected to MQTT")
    client.subscribe(TOPICS['knowledge_update'])
    client.subscribe(TOPICS['environment_update'])


def on_mqtt_message(client, userdata, msg):
    global current_knowledge, current_environment
    
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        
        if msg.topic == TOPICS['knowledge_update']:
            current_knowledge = payload
            socketio.start_background_task(broadcast_state)
        elif msg.topic == TOPICS['environment_update']:
            current_environment = payload
            socketio.start_background_task(broadcast_state)
    except Exception as e:
        print(f"[Web] Error: {e}")


def broadcast_state():
    global current_knowledge, current_environment
    
    if not current_knowledge or not current_environment:
        return
    
    grid = current_environment.get('grid', {})
    robot = current_environment.get('robot', {})
    k = current_knowledge
    
    pending_locs = [o['delivery_location'] for o in k.get('pending_orders', [])]
    
    seq_map = {}
    for i, loc in enumerate(k.get('delivery_sequence', [])):
        seq_map[f"{loc[0]},{loc[1]}"] = i + 1
    
    # Use original_last_delivery for path coloring (not current depleting sequence)
    last_del_loc = k.get('original_last_delivery')
    
    countdown = "-"
    pending = k.get('pending_orders', [])
    if pending and not k.get('mission_in_progress'):
        elapsed = time.time() - k.get('last_mission_start_time', time.time())
        remaining = k.get('mission_timeout', 30) - elapsed
        if remaining > 0:
            countdown = f"{int(remaining // 60):02d}:{int(remaining % 60):02d}"
        else:
            countdown = "Starting..."
    elif k.get('mission_in_progress'):
        countdown = "In progress"
    
    times = k.get('delivery_times', [])
    avg = sum(times) / len(times) if times else 0
    
    current_path = []
    if k.get('mission_in_progress') and k.get('current_plan'):
        current_path = k.get('current_plan', [])
    
    state = {
        'grid': grid.get('grid', []),
        'width': grid.get('width', 22),
        'height': grid.get('height', 15),
        'robot_position': robot.get('position', [1, 1]),
        'base_location': grid.get('base_location', [1, 1]),
        'delivery_locations': grid.get('delivery_locations', []),
        'dynamic_obstacles': grid.get('dynamic_obstacles', []),
        'pending_locations': pending_locs,
        'delivery_sequence': seq_map,
        'last_delivery_location': last_del_loc,
        'current_path': current_path,
        'current_path_index': k.get('current_plan_index', 0),
        'loaded_orders': len(k.get('loaded_orders', [])),
        'pending_count': len(pending),
        'is_stuck': k.get('is_stuck', False),
        'countdown': countdown,
        'mission_in_progress': k.get('mission_in_progress', False),
        'metrics': {
            'total_deliveries': len(k.get('completed_orders', [])),
            'total_distance': k.get('total_distance_traveled', 0),
            'replans': k.get('number_of_replans', 0),
            'avg_delivery_time': round(avg, 1)
        }
    }
    
    socketio.emit('state_update', state)


def connect_mqtt():
    global mqtt_client
    
    mqtt_client = mqtt.Client(client_id=f"web-{os.getpid()}")
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    
    for i in range(30):
        try:
            mqtt_client.connect(BROKER, PORT, 60)
            mqtt_client.loop_start()
            time.sleep(1)
            return
        except:
            print(f"[Web] Waiting for MQTT... ({i+1})")
            time.sleep(2)
    raise Exception("MQTT connection failed")


def init_system():
    mqtt_client.publish(TOPICS['system_init'], json.dumps({}))
    time.sleep(0.5)


def mape_loop():
    global running, mqtt_client
    
    while True:
        if running and mqtt_client:
            mqtt_client.publish(TOPICS['monitor_request'], json.dumps({}))
            broadcast_state()
        eventlet.sleep(0.4)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory('/app/assets', filename)


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
    
    row, col = data.get('row'), data.get('col')
    if row is None or col is None:
        return
    
    if current_environment:
        grid = current_environment.get('grid', {})
        if [row, col] in grid.get('delivery_locations', []):
            order_counter += 1
            mqtt_client.publish(TOPICS['user_add_order'], json.dumps({
                'order_id': f"ORD_{order_counter:03d}",
                'delivery_location': [row, col],
                'timestamp': time.time()
            }))
            print(f"[Web] Added order at [{row}, {col}]")
        else:
            mqtt_client.publish(TOPICS['user_toggle_obstacle'], json.dumps({
                'position': [row, col]
            }))
            print(f"[Web] Toggle obstacle at [{row}, {col}]")


@socketio.on('reset')
def handle_reset():
    global order_counter, current_knowledge, current_environment
    print("[Web] Reset")
    order_counter = 0
    current_knowledge = None
    current_environment = None
    mqtt_client.publish(TOPICS['system_reset'], json.dumps({}))


if __name__ == '__main__':
    print("[Web] Starting...")
    
    connect_mqtt()
    init_system()
    
    running = True
    eventlet.spawn(mape_loop)
    
    print("=" * 50)
    print("Autonomous Delivery Robot - MAPE-K via MQTT")
    print("http://localhost:5000")
    print("=" * 50)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)