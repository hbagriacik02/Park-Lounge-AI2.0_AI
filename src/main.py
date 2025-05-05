import os
from dotenv import load_dotenv
from MqttClient import MqttClient
from LicensePlateRecognizer import LicensePlateRecognizer

load_dotenv()
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

def handle_trigger(data, mqtt_client, recognizer):
    print("handle_trigger: Trigger empfangen mit Daten:", data)
    if data.get("command") is not None:
        print("Trigger received, start scan...")
        #if not recognizer.cap or not recognizer.cap.isOpened():
        #print("handle_trigger: Kamera nicht verfügbar.")
        response = {
            "status": "success",
            "plate": "BIE NE 74",
            "approved": True,
        }
        mqtt_client.publish_camera_detected_response(response)

        #ToDo: Camera scanning failed - fix it

        #plate, approved, screenshot_path = recognizer.scan_and_validate()
        #print(f"handle_trigger: Scan-Ergebnis: plate={plate}, approved={approved}, screenshot_path={screenshot_path}")
        #if plate is None and not approved and screenshot_path is None:
        #    response = {
        #        "status": "success",
        #        "plate": "BIE NE 74",
        #        "approved": False,
        #    }
        #else:
        #    response = {
        #        "status": "success",
        #        "plate": plate if plate else "UNKNOWN",
        #        "approved": approved
        #    }
        #mqtt_client.publish_camera_detected_response(response)
    else:
        print("handle_trigger: Ungültiger Trigger, kein 'command' gefunden.")
        mqtt_client.publish_camera_trigger_error_response()

def main():
    try:
        print("main: Initialisiere LicensePlateRecognizer...")
        recognizer = LicensePlateRecognizer()
        print("main: Initialisiere MqttClient...")
        mqtt_client = MqttClient(
            username=MQTT_USERNAME,
            password=MQTT_PASSWORD
        )
        mqtt_client.on_trigger_callback = lambda data: handle_trigger(data, mqtt_client, recognizer)
        print("main: Verbinde mit MQTT-Broker...")
        mqtt_client.connect()
        if recognizer.cap and recognizer.cap.isOpened():
            mqtt_client.publish_camera_detected_response({"status": "camera ready"})
            print("main: Kamera bereit, Status 'camera ready' gesendet.")
        else:
            mqtt_client.publish_camera_detected_response({"status": "failed"})
            print("main: Kamera nicht verfügbar, Status 'failed' gesendet.")
        try:
            print("main: Starte Hauptschleife...")
            while True:
                pass
        except KeyboardInterrupt:
            print("main: Programm durch Benutzer beendet.")
            if mqtt_client.is_connected_flag:
                mqtt_client.publish_camera_detected_response({"status": "camera disconnected"})
            mqtt_client.disconnect()
            recognizer.release()
    except Exception as e:
        print(f"main: Fehler im Hauptprogramm: {e}")
        if mqtt_client.is_connected_flag:
            mqtt_client.publish_camera_detected_response({"status": "failed", "error": str(e)})
        mqtt_client.disconnect()
        recognizer.release()

if __name__ == "__main__":
    main()