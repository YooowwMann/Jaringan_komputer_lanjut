import cv2
import socket
from ultralytics import YOLO

GCS_IP = "10.32.73.220"
GCS_PORT = 5001

CAMERA_DEVICE = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

JPEG_QUALITY = 40
CONFIDENCE = 0.4

print("Loading YOLO11n...")
model = YOLO("yolo11n.pt")
print("YOLO11n loaded")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

if not cap.isOpened():
    print("ERROR: kamera gagal dibuka")
    exit(1)

cap.set(
    cv2.CAP_PROP_FOURCC,
    cv2.VideoWriter_fourcc(*"MJPG")
)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)

print("Camera OK")
print(f"Sending YOLO11n frames to {GCS_IP}:{GCS_PORT}")

while True:

    ret, frame = cap.read()

    if not ret:
        print("Gagal membaca kamera")
        continue

    # YOLO11n inference
    results = model.predict(
        source=frame,
        conf=CONFIDENCE,
        verbose=False
    )

    # Tambahkan bounding box + label
    annotated_frame = results[0].plot()

    # Encode hasil YOLO menjadi JPEG
    ok, encoded = cv2.imencode(
        ".jpg",
        annotated_frame,
        [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    )

    if not ok:
        continue

    data = encoded.tobytes()

    try:
        sent = sock.sendto(
            data,
            (GCS_IP, GCS_PORT)
        )

        print(
            f"\rYOLO frame sent: {sent} bytes",
            end="",
            flush=True
        )

    except OSError as e:
        print(f"\nUDP ERROR: {e}")

cap.release()
sock.close()
