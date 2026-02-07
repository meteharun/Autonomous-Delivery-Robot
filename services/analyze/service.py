"""
Analyze Service - Analyzes monitoring data and decides adaptation.
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

client = None


def handle_message(client_obj, userdata, msg):
    global client
    
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8')) if msg.payload else {}
        
        if topic == TOPICS['monitor_result']:
            sensor_data = payload.get('sensor_data', {})
            knowledge = payload.get('knowledge', {})
            grid = payload.get('grid', {})
            
            analysis = {
                'requires_adaptation': False,
                'adaptation_type': None,
                'reason': None,
                'knowledge': knowledge,
                'grid': grid
            }
            
            mission_in_progress = sensor_data.get('mission_in_progress', False)
            loaded_orders = sensor_data.get('loaded_orders', [])
            is_at_base = payload.get('at_base', False)
            
            # Rule 1: Mission complete
            if mission_in_progress and not loaded_orders and is_at_base:
                analysis['requires_adaptation'] = True
                analysis['adaptation_type'] = 'end_mission'
                analysis['reason'] = 'Back at base'
                client.publish(TOPICS['analyze_result'], json.dumps(analysis))
                print("[Analyze] Decision: end_mission")
                return
            
            # Rule 2: At delivery location
            if payload.get('at_delivery_location') and loaded_orders:
                analysis['requires_adaptation'] = True
                analysis['adaptation_type'] = 'deliver'
                analysis['reason'] = 'At delivery location'
                client.publish(TOPICS['analyze_result'], json.dumps(analysis))
                print("[Analyze] Decision: deliver")
                return
            
            # Rule 3: Start mission
            if payload.get('needs_new_mission') and not mission_in_progress:
                analysis['requires_adaptation'] = True
                analysis['adaptation_type'] = 'start_mission'
                analysis['reason'] = 'Capacity or timeout'
                client.publish(TOPICS['analyze_result'], json.dumps(analysis))
                print("[Analyze] Decision: start_mission")
                return
            
            # Rule 4: Path blocked
            if payload.get('path_blocked') and mission_in_progress:
                analysis['requires_adaptation'] = True
                analysis['adaptation_type'] = 'replan'
                analysis['reason'] = 'Path blocked'
                client.publish(TOPICS['analyze_result'], json.dumps(analysis))
                print("[Analyze] Decision: replan (blocked)")
                return
            
            # Rule 5: Obstacle removed
            if payload.get('obstacle_removed') and mission_in_progress:
                analysis['requires_adaptation'] = True
                analysis['adaptation_type'] = 'replan'
                analysis['reason'] = 'Obstacle removed'
                client.publish(TOPICS['analyze_result'], json.dumps(analysis))
                print("[Analyze] Decision: replan (obstacle removed)")
                return
            
            # No adaptation needed
            client.publish(TOPICS['analyze_result'], json.dumps(analysis))
            print("[Analyze] Decision: continue")
    
    except Exception as e:
        print(f"[Analyze] Error: {e}")


def on_connect(client_obj, userdata, flags, rc):
    print("[Analyze] Connected to MQTT")
    client_obj.subscribe(TOPICS['monitor_result'])


if __name__ == '__main__':
    print("[Analyze] Starting...")
    
    client = mqtt.Client(client_id=f"analyze-{uuid.uuid4().hex[:8]}")
    client.on_connect = on_connect
    client.on_message = handle_message
    
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            break
        except:
            print("[Analyze] Waiting for MQTT...")
            time.sleep(2)
    
    print("[Analyze] Ready")
    client.loop_forever()