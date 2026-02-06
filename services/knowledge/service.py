"""
Knowledge Service - Maintains shared state via MQTT.
Listens for state updates and provides current state on request.
"""
import sys
import time

sys.path.insert(0, '/app')
from shared.mqtt_client import MQTTClient, Topics
from shared.state_models import create_initial_knowledge, create_order

# In-memory state
knowledge = None


def handle_init(payload):
    """Initialize knowledge state."""
    global knowledge
    base_location = payload.get('base_location', [1, 1])
    max_capacity = payload.get('max_capacity', 3)
    knowledge = create_initial_knowledge(tuple(base_location), max_capacity)
    print(f"[Knowledge] Initialized with base at {base_location}")
    publish_state()


def handle_reset(payload):
    """Reset knowledge state."""
    handle_init(payload)


def handle_add_order(payload):
    """Add a new order."""
    global knowledge
    if knowledge is None:
        return
    
    order = create_order(
        payload['order_id'],
        tuple(payload['delivery_location']),
        payload.get('timestamp', time.time())
    )
    knowledge['pending_orders'].append(order)
    
    if len(knowledge['pending_orders']) == 1:
        knowledge['last_mission_start_time'] = time.time()
    
    print(f"[Knowledge] Added order {order['order_id']}")
    publish_state()


def handle_update(payload):
    """Update knowledge fields."""
    global knowledge
    if knowledge is None:
        return
    
    for key, value in payload.items():
        if key in knowledge:
            knowledge[key] = value
    
    # Debug: show what changed
    if 'current_plan_index' in payload:
        print(f"[Knowledge] Updated plan_index to {payload['current_plan_index']}")
    if 'mission_in_progress' in payload:
        print(f"[Knowledge] mission_in_progress = {payload['mission_in_progress']}")
    
    publish_state()


def publish_state():
    """Publish current knowledge state."""
    global knowledge, client
    if knowledge:
        client.publish(Topics.KNOWLEDGE_UPDATE, knowledge)


def handle_monitor_request(payload):
    """Provide knowledge state for monitor."""
    publish_state()


if __name__ == '__main__':
    print("[Knowledge] Service starting...")
    
    client = MQTTClient('knowledge-service')
    client.connect()
    
    # Subscribe to topics
    client.subscribe(Topics.SYSTEM_INIT, handle_init)
    client.subscribe(Topics.SYSTEM_RESET, handle_reset)
    client.subscribe(Topics.USER_ADD_ORDER, handle_add_order)
    client.subscribe(Topics.MONITOR_REQUEST, handle_monitor_request)
    client.subscribe('knowledge/set', handle_update)  # For Execute to update state
    
    print("[Knowledge] Service ready, waiting for messages...")
    client.loop_forever()