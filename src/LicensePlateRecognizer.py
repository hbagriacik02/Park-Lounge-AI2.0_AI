import cv2 as cv
import pytesseract as tess
from ultralytics import YOLO

def cv_camera():
    model = YOLO('yolov8n.pt')  # Ersetze durch ein Kennzeichen-Modell
    cap = cv.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame)
        for result in results:
            boxes = result.boxes.xyxy  # Bounding-Box-Koordinaten
            for box in boxes:
                x1, y1, x2, y2 = map(int, box[:4])
                cv.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)  # Zeichne Rechteck
        cv.imshow("YOLO Detection", frame)
        if cv.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv.destroyAllWindows()