import cv2
import socket
import time
from ultralytics import YOLO

# ============================================================
# CONFIGURATION
# ============================================================

GCS_IP = "10.32.73.220"
GCS_PORT = 5001

CAMERA_DEVICE = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

JPEG_QUALITY = 40
CONFIDENCE = 0.4

# ============================================================
# LOAD YOLO11n
# ============================================================

print("Loading YOLO11n...")

model = YOLO("yolo11n.pt")

print("YOLO11n loaded.")

# ============================================================
# UDP SOCKET
# ============================================================

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ============================================================
# CAMERA
# ============================================================

cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

if not cap.isOpened():
    print("ERROR: Kamera gagal dibuka!")
    exit(1)

# Force MJPG to avoid green frames
cap.set(
    cv2.CAP_PROP_FOURCC,
    cv2.VideoWriter_fourcc(*"MJPG")
)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)

print("Camera opened.")
print(f"Streaming to {GCS_IP}:{GCS_PORT}")
print("Press Ctrl+C to stop.")

# ============================================================
# MAIN LOOP
# ============================================================

frame_count = 0
start_time = time.time()

try:

    while True:

        ret, frame = cap.read()

        if not ret:
            print("WARNING: gagal membaca frame kamera")
            continue

        # ----------------------------------------------------
        # YOLO11n INFERENCE
        # ----------------------------------------------------

        results = model.predict(
            source=frame,
            conf=CONFIDENCE,
            verbose=False
        )

        # Draw bounding boxes
        annotated_frame = results[0].plot()

        # ----------------------------------------------------
        # JPEG ENCODE
        # ----------------------------------------------------

        success, encoded = cv2.imencode(
            ".jpg",
            annotated_frame,
            [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
        )

        if not success:
            print("WARNING: gagal encode JPEG")
            continue

        data = encoded.tobytes()

        # ----------------------------------------------------
        # UDP SEND
        # ----------------------------------------------------

        try:

            sock.sendto(
                data,
                (GCS_IP, GCS_PORT)
            )

        except OSError as e:

            print(f"\nNetwork error: {e}")
            print("Mencoba melanjutkan...")
            continue

        # ----------------------------------------------------
        # STATISTICS
        # ----------------------------------------------------

        frame_count += 1

        elapsed = time.time() - start_time

        if elapsed >= 5:

            current_fps = frame_count / elapsed

            print(
                f"FPS: {current_fps:.2f} | "
                f"Frame: {frame_count} | "
                f"JPEG: {len(data) / 1024:.1f} KB"
            )

            frame_count = 0
            start_time = time.time()

except KeyboardInterrupt:

    print("\nStopping sender...")

finally:

    cap.release()
    sock.close()

    print("Sender stopped.")
