import json
import paho.mqtt.client as mqtt

CAMERA_STATUS_TOPIC = "parkhaus/camera/response"
CAMERA_TRIGGER_TOPIC = "parkhaus/camera/trigger"
CAR_PARK_STATUS_TOPIC = "parkhaus/status"

class MqttClient:
    def __init__(self, username, password):
        self.port = 1883
        self.username = username
        self.broker = "192.168.144.206"
        self.car_park_status_topic = CAR_PARK_STATUS_TOPIC
        self.camera_trigger_topic = CAMERA_TRIGGER_TOPIC
        self.camera_status_topic = CAMERA_STATUS_TOPIC
        self.client = mqtt.Client()
        self.client.username_pw_set(username=username, password=password)
        self.on_trigger_callback = None
        self.is_connected_flag = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            print(f"Connected to broker: '{self.broker}' with user: '{self.username}'")
            self.is_connected_flag = True
            self.client.subscribe(self.camera_trigger_topic)
            self.client.subscribe(self.car_park_status_topic)
            print(f"Subscribed to {self.camera_trigger_topic}")
            print(f"Subscribed to {self.car_park_status_topic}")
        else:
            print(f"Failed to connect, return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        print("Disconnected from MQTT Broker")
        self.is_connected_flag = False

    def received_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode()
            print(f"Incoming request on {msg.topic}: {payload}")
            if msg.topic == self.camera_trigger_topic and self.on_trigger_callback:
                data = json.loads(payload)
                self.on_trigger_callback(data)
        except Exception as e:
            print(f"Could not process message: {e}")

    def on_publish(self, client, userdata, mid):
        pass

    def connect(self):
        try:
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.received_message
            self.client.on_publish = self.on_publish
            self.client.connect(self.broker, self.port)
            self.client.loop_start()
        except Exception as e:
            print(f"Connection error: {e}")
            self.is_connected_flag = False

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.is_connected_flag = False

    def publish_camera_status(self, message):
        try:
            result = self.client.publish(self.camera_status_topic, json.dumps({'status': message}))
            print(f"Outgoing response to {self.camera_status_topic}: {json.dumps({'status': message})}")
            return result
        except Exception as e:
            print(f"Publish error: {e}")
            return None

    def publish_camera_detected_response(self, message):
        try:
            result = self.client.publish(self.camera_status_topic, json.dumps(message))
            print(f"Outgoing response to {self.camera_status_topic}: {json.dumps(message)}")
            return result
        except Exception as e:
            print(f"Publish error: {e}")
            return None

    def publish_camera_trigger_error_response(self):
        try:
            result = self.client.publish(self.camera_status_topic, json.dumps({"message": "Invalid trigger message received"}))
            print(f"Outgoing response to {self.camera_status_topic}: {json.dumps({'message': 'Invalid trigger message received'})}")
            return result
        except Exception as e:
            print(f"Publish error: {e}")
            return None