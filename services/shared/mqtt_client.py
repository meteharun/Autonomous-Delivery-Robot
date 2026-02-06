"""
MQTT Client helper for all services.
Each service connects to the MQTT broker and subscribes to topics.
"""
import paho.mqtt.client as mqtt
import json
import os
import time
import uuid


MQTT_BROKER = os.environ.get('MQTT_BROKER', 'mqtt')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))


# Topic definitions
class Topics:
    # Commands/triggers
    SYSTEM_INIT = 'system/init'
    SYSTEM_RESET = 'system/reset'
    
    # User actions
    USER_ADD_ORDER = 'user/add_order'
    USER_TOGGLE_OBSTACLE = 'user/toggle_obstacle'
    
    # MAPE-K flow
    MONITOR_REQUEST = 'mape/monitor/request'
    MONITOR_RESULT = 'mape/monitor/result'
    
    ANALYZE_RESULT = 'mape/analyze/result'
    
    PLAN_RESULT = 'mape/plan/result'
    
    EXECUTE_RESULT = 'mape/execute/result'
    
    # State updates
    KNOWLEDGE_UPDATE = 'knowledge/update'
    ENVIRONMENT_UPDATE = 'environment/update'


class MQTTClient:
    """Wrapper around paho MQTT client for easier use."""
    
    def __init__(self, service_name: str):
        # Use unique client ID with UUID to avoid conflicts
        self.client_id = f"{service_name}-{uuid.uuid4().hex[:8]}"
        self.service_name = service_name
        self.client = mqtt.Client(client_id=self.client_id, clean_session=True)
        self.handlers = {}
        self.connected = False
        self.subscriptions = []
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[{self.service_name}] Connected to MQTT broker")
            self.connected = True
            # Subscribe to all registered topics
            for topic in self.subscriptions:
                self.client.subscribe(topic, qos=0)
                print(f"[{self.service_name}] Subscribed to {topic}")
        else:
            print(f"[{self.service_name}] Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        print(f"[{self.service_name}] Disconnected (rc={rc})")
        self.connected = False
    
    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            
            if topic in self.handlers:
                self.handlers[topic](payload)
        except Exception as e:
            print(f"[{self.service_name}] Error processing message: {e}")
    
    def connect(self, retries=30):
        """Connect to MQTT broker with retries."""
        for i in range(retries):
            try:
                self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
                return True
            except Exception as e:
                print(f"[{self.service_name}] Connection attempt {i+1} failed: {e}")
                time.sleep(2)
        
        raise Exception(f"Could not connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}")
    
    def subscribe(self, topic: str, handler):
        """Subscribe to a topic with a handler function."""
        self.handlers[topic] = handler
        self.subscriptions.append(topic)
    
    def publish(self, topic: str, payload: dict):
        """Publish a message to a topic."""
        msg = json.dumps(payload)
        self.client.publish(topic, msg, qos=0)
    
    def loop_forever(self):
        """Block and process messages forever."""
        self.client.loop_forever()
    
    def loop_start(self):
        """Start background thread for processing."""
        self.client.loop_start()
    
    def loop_stop(self):
        """Stop background thread."""
        self.client.loop_stop()
    
    def disconnect(self):
        """Disconnect from broker."""
        self.client.disconnect()