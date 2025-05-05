import os
import cv2
import time
import platform
import subprocess
import pytesseract
import numpy as np
from ultralytics import YOLO
from datetime import datetime, timedelta
from LogHandler import LogHandler

# Plattformübergreifender Tesseract-Pfad
if platform.system() == "Windows":
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:
    tesseract_path = '/usr/bin/tesseract'

# Überprüfe, ob der Tesseract-Pfad existiert
if not os.path.exists(tesseract_path):
    raise FileNotFoundError(
        f"Tesseract nicht gefunden unter: {tesseract_path}. Bitte installiere Tesseract und überprüfe den Pfad.")
pytesseract.pytesseract.tesseract_cmd = tesseract_path
print(f"Tesseract-Pfad gesetzt: {tesseract_path}")

class LicensePlateRecognizer:
    def __init__(self, model_path='../license_plate_detector.pt', access_allowed_file='../access_allowed.csv'):
        print("LicensePlateRecognizer: Initialisiere...")
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            raise Exception(f"Fehler beim Laden des YOLO-Modells: {e}")
        self.log_handler = LogHandler(access_allowed_file=access_allowed_file)
        self.cap = None
        system = platform.system()
        camera_indices = [0, 1, 2, 4, 6]
        backends = [cv2.CAP_ANY]
        if system == "Windows":
            backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
            print("Windows erkannt. Verwende Windows-spezifische Kamera-Backends.")
        else:
            backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
            try:
                result = subprocess.run(['ls', '-l', '/dev/video0'], capture_output=True, text=True)
                print(f"Kamera-Berechtigungen: {result.stdout.strip()}")
            except Exception as e:
                print(f"Fehler beim Überprüfen der Kamera-Berechtigungen: {e}")

        # Kamera öffnen
        for index in camera_indices:
            for backend in backends:
                backend_name = {cv2.CAP_V4L2: "V4L2", cv2.CAP_DSHOW: "DSHOW", cv2.CAP_MSMF: "MSMF",
                                cv2.CAP_ANY: "ANY"}.get(backend, "UNKNOWN")
                print(f"Versuche Kamera mit Index {index} und Backend {backend_name}...")
                self.cap = cv2.VideoCapture(index, backend)
                if self.cap.isOpened():
                    print(f"Kamera erfolgreich geöffnet mit Index {index} und Backend {backend_name}.")
                    break
            if self.cap and self.cap.isOpened():
                break

        if not self.cap or not self.cap.isOpened():
            raise Exception("Keine Kamera konnte geöffnet werden. Überprüfe die Kamera-Verbindung oder Berechtigungen.")

        # Teste einen Frame
        time.sleep(1)
        ret, test_frame = self.cap.read()
        if not ret or test_frame is None or not isinstance(test_frame, np.ndarray):
            self.cap.release()
            raise Exception("Kamera liefert keine Frames. Überprüfe die Kamera-Hardware oder Treiber.")
        print(f"Test-Frame geladen: Shape={test_frame.shape}, Type={test_frame.dtype}")

        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if self.frame_width == 0 or self.frame_height == 0:
            self.cap.release()
            raise Exception("Ungültige Kamera-Auflösung.")
        print(f"Kamera-Auflösung: {self.frame_width}x{self.frame_height}")

        self.roi_width = int(self.frame_width * 0.8)
        self.roi_height = int(self.frame_height * 0.3)
        self.roi_x = (self.frame_width - self.roi_width) // 2
        self.roi_y = (self.frame_height - self.roi_height) // 2
        self.roi_color = (0, 0, 255)
        self.is_scanning = False
        self.scan_start_time = None
        self.scan_duration = timedelta(seconds=30)
        self.scan_cooldown = timedelta(seconds=10)
        self.last_scan_end = None
        self.collected_plates = set()
        self.access_status = None
        self.access_color = None
        self.last_denied_plate = None
        self.last_screenshot_time = None
        self.screenshot_timeout = timedelta(seconds=20)

        # OpenCV GUI-Unterstützung prüfen
        if "GUI" not in cv2.getBuildInformation():
            print("Warnung: OpenCV ohne GUI-Unterstützung kompiliert. Fenster werden nicht angezeigt.")
        if system == "Linux":
            print("Hinweis: Bei Wayland-Problemen starte mit 'export QT_QPA_PLATFORM=xcb'.")

    def preprocess_plate(self, plate_img):
        if plate_img is None or not isinstance(plate_img, np.ndarray):
            print("preprocess_plate: Ungültiges Bild.")
            return None
        scale_factor = 2
        plate_img = cv2.resize(plate_img, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        thresh = cv2.bitwise_not(thresh)
        return thresh

    def extract_plate_text(self, plate_img):
        processed_img = self.preprocess_plate(plate_img)
        if processed_img is None:
            return ""
        config = '--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(processed_img, config=config)
        text = ''.join(c for c in text if c.isalnum()).strip()
        text = text.replace('s', '').replace('S', '')
        return text

    def draw_roi(self, frame):
        if frame is None or not isinstance(frame, np.ndarray):
            print("draw_roi: Ungültiger Frame.")
            return frame
        top_left = (self.roi_x, self.roi_y)
        bottom_right = (self.roi_x + self.roi_width, self.roi_y + self.roi_height)
        cv2.rectangle(frame, top_left, bottom_right, self.roi_color, 2)
        return frame

    def is_in_roi(self, bbox):
        x1, y1, x2, y2 = bbox
        roi_x1, roi_y1 = self.roi_x, self.roi_y
        roi_x2, roi_y2 = self.roi_x + self.roi_width, self.roi_y + self.roi_height
        return (x1 >= roi_x1 and y1 >= roi_y1 and x2 <= roi_x2 and y2 <= roi_y2)

    def evaluate_collected_plates(self, frame):
        for plate in self.collected_plates:
            if self.log_handler.validate_is_plate_allowed(plate):
                self.access_status = "Access Granted"
                self.access_color = (0, 255, 0)
                return plate, True, None
        self.access_status = "Access Denied"
        self.access_color = (0, 0, 255)
        if self.collected_plates and (self.last_screenshot_time is None or
                                      datetime.now() - self.last_screenshot_time > self.screenshot_timeout):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = f'../log/img/snapshot-{timestamp}.jpg'
            self.last_screenshot_time = datetime.now()
            if frame is not None and isinstance(frame, np.ndarray):
                cv2.imwrite(screenshot_path, frame)
                print(f"Screenshot gespeichert: {screenshot_path}")
            return next(iter(self.collected_plates)), False, screenshot_path
        return next(iter(self.collected_plates)) if self.collected_plates else None, False, None

    def process_frame(self, frame):
        if frame is None or not isinstance(frame, np.ndarray):
            print("process_frame: Ungültiger Frame empfangen.")
            return None

        current_time = datetime.now()
        self.roi_color = (0, 0, 255)
        frame = self.draw_roi(frame)
        if frame is None:
            print("process_frame: draw_roi hat None zurückgegeben.")
            return None

        if self.is_scanning and self.scan_start_time:
            if current_time - self.scan_start_time > self.scan_duration:
                self.is_scanning = False
                self.last_scan_end = current_time
                print("process_frame: Scan beendet. Auswertung der gesammelten Kennzeichen...")
                plate, approved, screenshot_path = self.evaluate_collected_plates(frame)
                if screenshot_path and plate:
                    self.log_handler.log_denied_access(plate, screenshot_path)
                self.collected_plates.clear()
                return frame

        if not self.is_scanning and (self.last_scan_end is None or
                                     current_time - self.last_scan_end > self.scan_cooldown):
            self.is_scanning = True
            self.scan_start_time = current_time
            self.collected_plates.clear()
            self.access_status = None
            print("process_frame: Neuer Scan gestartet.")

        if self.is_scanning:
            cv2.putText(frame, "Scanning License Plate...", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)
            results = self.model(frame)
            best_conf = 0
            best_bbox = None
            best_label = None

            if results and len(results) > 0:
                for result in results:
                    if hasattr(result, 'boxes') and result.boxes is not None:
                        boxes = result.boxes
                        for box in boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            label = self.model.names[int(box.cls)]
                            conf = box.conf.item()
                            if self.is_in_roi((x1, y1, x2, y2)) and label in ['license_plate', 'car'] and conf > 0.3:
                                if conf > best_conf:
                                    best_conf = conf
                                    best_bbox = (x1, y1, x2, y2)
                                    best_label = label
                            print(
                                f"process_frame: Erkannt: {label}, Konfidenz: {conf:.2f}, In ROI: {self.is_in_roi((x1, y1, x2, y2))}")

            if best_bbox:
                self.roi_color = (255, 255, 0)
                x1, y1, x2, y2 = best_bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f'{best_label} {best_conf:.2f}', (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                plate_img = frame[y1:y2, x1:x2]
                plate_text = self.extract_plate_text(plate_img)
                if plate_text:
                    self.collected_plates.add(plate_text)
                    print(f"process_frame: Erkanntes Kennzeichen: {plate_text}")

        elif self.last_scan_end and current_time - self.last_scan_end <= self.scan_cooldown:
            cv2.putText(frame, "Cooldown: Waiting for next scan...", (50, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)

        if self.access_status:
            cv2.putText(frame, self.access_status, (50, self.frame_height - 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, self.access_color, 3)
            if self.access_status == "Access Denied":
                cv2.putText(frame, "Your license plate has been recorded",
                            (50, self.frame_height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.access_color, 2)

        frame = self.draw_roi(frame)
        if frame is None:
            print("process_frame: draw_roi hat None zurückgegeben (am Ende).")
            return None
        return frame

    def scan_and_validate(self):
        print("scan_and_validate: Starte Scan...")
        ret, frame = self.cap.read()
        if not ret or frame is None or not isinstance(frame, np.ndarray):
            print("scan_and_validate: Fehler beim Lesen des Frames.")
            return None, False, None

        print(f"scan_and_validate: Frame geladen: Shape={frame.shape}, Type={frame.dtype}")
        self.is_scanning = True
        self.scan_start_time = datetime.now()
        self.collected_plates.clear()
        frame = self.process_frame(frame)
        if frame is None:
            print("scan_and_validate: process_frame hat None zurückgegeben.")
            return None, False, None

        self.is_scanning = False
        self.last_scan_end = datetime.now()
        plate, approved, screenshot_path = self.evaluate_collected_plates(frame)
        print(f"scan_and_validate: Ergebnis: plate={plate}, approved={approved}, screenshot_path={screenshot_path}")

        if screenshot_path and plate:
            self.log_handler.log_denied_access(plate, screenshot_path)

        self.collected_plates.clear()

        return plate, approved, screenshot_path

    def run(self):
        print("run: Starte Kamera-Feed...")
        cv2.namedWindow('License Plate Recognition', cv2.WINDOW_NORMAL)
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret or frame is None or not isinstance(frame, np.ndarray):
                    print("run: Fehler beim Lesen des Frames. Überprüfe die Kamera-Verbindung.")
                    break
                print(f"run: Frame geladen: Shape={frame.shape}, Type={frame.dtype}")
                frame = self.process_frame(frame)
                if frame is None:
                    print("run: process_frame hat None zurückgegeben.")
                    break
                try:
                    cv2.imshow('License Plate Recognition', frame)
                except cv2.error as e:
                    print(f"run: Fehler bei cv2.imshow: {e}")
                    break
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("run: Programm durch Benutzer beendet (q gedrückt).")
                    break
        finally:
            self.cap.release()
            cv2.destroyAllWindows()
            print("run: Kamera freigegeben und Fenster geschlossen.")

    def release(self):
        print("release: Freigebe Kamera und schließe Fenster...")
        self.cap.release()
        cv2.destroyAllWindows()

#if __name__ == '__main__':
#    try:
#        recognizer = LicensePlateRecognizer()
#        recognizer.run()
#    except Exception as e:
#        print(f"Fehler beim Ausführen des Programms: {e}")