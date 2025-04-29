import LogHandler as loghandler
from MqttClient import MqttClient

APPROVED = False

def handle_trigger(data, mqtt_client):
    if data.get("command") is not None:
        response = {
            "status": "success",
            "plate": "AB123CD",
            "approved": APPROVED
        }
        mqtt_client.publish_camera_detected_response(response)
    else:
        mqtt_client.publish_camera_trigger_error_response()

def main():
    mqtt_client = MqttClient("client", "123456")
    mqtt_client.on_trigger_callback = lambda data: handle_trigger(data, mqtt_client)
    mqtt_client.connect()

    if mqtt_client.get_mqtt_connection_status():
        mqtt_client.publish_camera_status("success") # Wenn die Kamera funktioniert
        mqtt_client.publish_camera_status("camera is ready")
        loghandler.validate_is_plate_allowed()# CSV Check
    else:
        mqtt_client.publish_camera_status("failed") # Wenn die Kamera nicht funktioniert
        mqtt_client.publish_camera_status("camera is not ready")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        mqtt_client.publish_camera_status("camera disconnected")
        mqtt_client.disconnect()

if __name__ == '__main__':
    main()