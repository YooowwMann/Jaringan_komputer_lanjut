import cv2
import socket
from ultralytics import YOLO

GCS_IP = "10.90.24.33"
GCS_PORT = 5002

# Load YOLO11n
model = YOLO("yolo11n.pt")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Kamera MJPG
cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    print("❌ Kamera gagal dibuka")
    exit()

print("✅ Kamera berhasil dibuka")
print("🤖 YOLO11n aktif")
print(f"📡 Mengirim ke {GCS_IP}:{GCS_PORT}")

frame_id = 0

while True:
    ret, frame = cap.read()

    if not ret:
        print("❌ Gagal membaca frame")
        break

    # YOLO11n inference
    results = model.predict(
        source=frame,
        conf=0.4,
        verbose=False
    )

    # Frame dengan bounding box YOLO
    annotated_frame = results[0].plot()

    # Encode ke JPEG
    success, encoded = cv2.imencode(
        ".jpg",
        annotated_frame,
        [cv2.IMWRITE_JPEG_QUALITY, 40]
    )

    if not success:
        continue

    data = encoded.tobytes()

    # Kirim langsung sebagai JPEG
    try:
        sock.sendto(data, (GCS_IP, GCS_PORT))
    except OSError as e:
        print(f"\n⚠️ Network error: {e}")
        print("🔄 Mencoba melanjutkan...")
        continue

    print(
        f"\rFrame: {frame_id} | "
        f"JPEG: {len(data)} bytes",
        end=""
    )

    frame_id += 1

cap.release()
sock.close()
