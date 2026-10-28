import os
import json
import socket
import struct
import time
import numpy as np
import cv2

# ============================================================
# KONFIGURASI RECEIVER
# ============================================================
LISTEN_IP = "0.0.0.0"       # Dengarkan dari semua interface jaringan
LISTEN_PORT = 5002          # Port UDP yang telah diverifikasi
BUFFER_SIZE = 65535         # Buffer socket UDP (maksimal paket UDP)
FRAME_TIMEOUT = 0.2         # Timeout 0.2s untuk membuang frame tertinggal (low-latency)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
LATEST_GPS_FILE = os.path.join(SCRIPT_DIR, "latest_gps.json")
LATEST_FRAME_FILE = os.path.join(SCRIPT_DIR, "latest_frame.jpg")

MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_FILE = os.path.join(MODELS_DIR, "face_recognizer.xml")
LABELS_FILE = os.path.join(MODELS_DIR, "labels.json")
CASCADE_FILE = os.path.join(MODELS_DIR, "haarcascade_frontalface_default.xml")

# Header format: !IHH (Network byte order / Big-endian)
# - I: frame_id (4 bytes unsigned int)
# - H: chunk_id (2 bytes unsigned short)
# - H: total_chunks (2 bytes unsigned short)
HEADER_STRUCT = "!IHH"
HEADER_SIZE = struct.calcsize(HEADER_STRUCT)  # 8 bytes

# Inisialisasi Face Recognition (LBPH & Haar Cascade)
recognizer = None
labels_map = {}
face_cascade = cv2.CascadeClassifier(CASCADE_FILE)

def reload_face_model():
    """Memuat model face recognition jika sudah selesai dilatih."""
    global recognizer, labels_map
    if os.path.exists(MODEL_FILE) and os.path.exists(LABELS_FILE):
        try:
            rec = cv2.face.LBPHFaceRecognizer_create()
            rec.read(MODEL_FILE)
            with open(LABELS_FILE, "r") as f:
                raw_labels = json.load(f)
                labels_map = {int(k): v for k, v in raw_labels.items()}
            recognizer = rec
            return True
        except Exception as e:
            print(f"[!] Gagal membaca model wajah: {e}")
    return False

def read_gps_cache():
    """Membaca cache GPS terbaru non-blocking."""
    if not os.path.exists(LATEST_GPS_FILE):
        return None
    try:
        with open(LATEST_GPS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

def process_face_recognition(frame):
    """
    Mendeteksi wajah manusia:
    - Jika cocok dengan Orang 1 / Orang 2: Bounding box HIJAU dengan Nama + Persentase.
    - Jika orang lain (orang asing / dosen): Bounding box MERAH dengan label [UNKNOWN].
    """
    global recognizer, labels_map
    if recognizer is None or face_cascade.empty():
        return frame

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.15,
        minNeighbors=5,
        minSize=(50, 50)
    )

    for (x, y, w, h) in faces:
        face_roi = gray[y : y + h, x : x + w]
        face_resized = cv2.resize(face_roi, (200, 200))

        try:
            label_id, distance = recognizer.predict(face_resized)
            # Di LBPH: distance < 75.0 dianggap cocok (jarak makin kecil makin mirip)
            if distance < 75.0 and label_id in labels_map:
                name = labels_map[label_id]
                color = (0, 255, 0)  # Hijau untuk orang yang dikenali
                conf_pct = max(0, min(100, int(100 - (distance * 0.7))))
                label_text = f"{name} ({conf_pct}%)"
            else:
                name = "UNKNOWN"
                color = (0, 0, 255)  # Merah untuk orang asing
                label_text = "[UNKNOWN]"
        except Exception:
            color = (0, 0, 255)
            label_text = "[UNKNOWN]"

        # Gambar bounding box kotak
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        # Background teks nama di atas kotak
        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        bg_y1 = max(0, y - th - 8)
        cv2.rectangle(frame, (x, bg_y1), (x + tw + 6, y), color, -1)
        cv2.putText(
            frame,
            label_text,
            (x + 3, max(th, y - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2
        )

    return frame

def draw_hud(frame, gps_data, current_fps):
    """
    Menggambar Head-Up Display (HUD / OSD) telemetri pada video frame GCS.
    """
    h, w = frame.shape[:2]
    now = time.time()

    # Buat overlay semi-transparan untuk header & footer bar
    overlay = frame.copy()
    bar_height = 34
    cv2.rectangle(overlay, (0, 0), (w, bar_height), (20, 20, 20), -1)
    cv2.rectangle(overlay, (0, h - bar_height), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

    # 1. Header: Status Drone & FPS
    is_gps_fresh = False
    gps_age_str = "N/A"

    if gps_data:
        local_rx = gps_data.get("local_received_at", 0)
        age = max(0.0, now - local_rx)
        gps_age_str = f"{age:.1f}s lalu"
        is_gps_fresh = not gps_data.get("is_stale", False) and (age <= 5.0)

    if gps_data and is_gps_fresh:
        status_text = "DRONE 1 : ONLINE"
        status_color = (0, 255, 0)      # Hijau
    elif gps_data:
        status_text = "DRONE 1 : GPS BASI"
        status_color = (0, 165, 255)    # Oranye
    else:
        status_text = "DRONE 1 : NO GPS DATA"
        status_color = (150, 150, 150)  # Abu-abu

    cv2.putText(frame, status_text, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)
    fps_text = f"FPS: {current_fps:.1f} | UDP: {LISTEN_PORT}"
    cv2.putText(frame, fps_text, (w - 180, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

    # 2. Footer: Koordinat GPS & Update
    if gps_data and "lat" in gps_data and "lon" in gps_data:
        lat = gps_data["lat"]
        lon = gps_data["lon"]
        acc = gps_data.get("accuracy_m")
        acc_str = f"±{acc:.1f}m" if acc is not None else "±?m"
        coord_text = f"LAT: {lat:.6f}  LON: {lon:.6f} ({acc_str})"
    else:
        coord_text = "LAT: --.------  LON: ---.------"

    cv2.putText(frame, coord_text, (12, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)
    update_text = f"GPS: {gps_age_str}"
    cv2.putText(frame, update_text, (w - 140, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 1)

    return frame

def run_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Perbesar buffer receive socket OS agar tidak ada paket tercecer di level kernel
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2 * 1024 * 1024) # 2 MB
    except OSError:
        pass

    sock.bind((LISTEN_IP, LISTEN_PORT))
    print("==================================================")
    print("     GCS VIDEO RECEIVER & TELEMETRY HUD (DRONE 1) ")
    print("==================================================")
    print(f"[*] Mendengarkan pada UDP {LISTEN_IP}:{LISTEN_PORT}")
    print(f"[*] Snapshot disimpan ke: {LATEST_FRAME_FILE}")
    
    # Coba muat model face recognition jika sudah ada
    has_face_model = reload_face_model()
    if has_face_model:
        print(f"[*] Model Face Recognition AKTIF: {list(labels_map.values())}")
    else:
        print("[*] Info: Model wajah belum dilatih. Jalankan 'python train_faces.py' setelah dataset diisi.")
        
    print("[*] Tekan 'q' pada jendela video atau CTRL+C untuk berhenti.\n")

    active_frames = {}
    last_stat_time = time.time()
    last_gps_read_time = 0.0
    last_snapshot_time = 0.0
    last_model_check_time = 0.0
    frames_received_count = 0
    total_bytes_count = 0
    current_fps = 0.0
    cached_gps = None

    try:
        while True:
            packet, addr = sock.recvfrom(BUFFER_SIZE)
            now = time.time()
            total_bytes_count += len(packet)

            # Validasi ukuran paket minimal harus memiliki header
            if len(packet) < HEADER_SIZE:
                continue

            # Parsing header
            frame_id, chunk_id, total_chunks = struct.unpack(
                HEADER_STRUCT, packet[:HEADER_SIZE]
            )
            payload = packet[HEADER_SIZE:]

            # Buat entry baru jika frame_id belum pernah dicatat
            if frame_id not in active_frames:
                active_frames[frame_id] = {
                    "chunks": {},
                    "total": total_chunks,
                    "first_seen": now
                }

            # Simpan payload chunk
            active_frames[frame_id]["chunks"][chunk_id] = payload

            # Cek apakah semua chunk untuk frame_id ini sudah lengkap
            if len(active_frames[frame_id]["chunks"]) == total_chunks:
                chunks_dict = active_frames[frame_id]["chunks"]
                del active_frames[frame_id]

                try:
                    jpeg_bytes = b"".join(chunks_dict[i] for i in range(total_chunks))
                except KeyError:
                    continue

                # Decode JPEG ke citra OpenCV
                np_arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                if frame is not None:
                    frames_received_count += 1

                    # Cek berkala apakah model wajah baru selesai dilatih (tiap 5 detik)
                    if recognizer is None and (now - last_model_check_time) >= 5.0:
                        reload_face_model()
                        last_model_check_time = now

                    # 1. Deteksi Wajah & Bounding Box Nama / UNKNOWN
                    frame = process_face_recognition(frame)

                    # 2. Perbarui cache GPS secara berkala (tiap 0.3s)
                    if (now - last_gps_read_time) >= 0.3:
                        cached_gps = read_gps_cache()
                        last_gps_read_time = now

                    # 3. Gambar Head-Up Display (HUD) telemetri di frame
                    hud_frame = draw_hud(frame, cached_gps, current_fps)

                    # 4. Simpan snapshot frame terkini untuk Bot Telegram /photo
                    if (now - last_snapshot_time) >= 0.3:
                        try:
                            cv2.imwrite(LATEST_FRAME_FILE, hud_frame)
                            last_snapshot_time = now
                        except Exception:
                            pass

                    # 5. Tampilkan frame di jendela OpenCV
                    cv2.imshow("GCS Video & Telemetry (Drone 1)", hud_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

            # Bersihkan frame kadaluarsa
            expired_keys = [
                fid for fid, data in active_frames.items()
                if (now - data["first_seen"]) > FRAME_TIMEOUT
            ]
            for fid in expired_keys:
                del active_frames[fid]

            # Hitung FPS setiap 1.5 detik
            if (now - last_stat_time) >= 1.5:
                elapsed = now - last_stat_time
                current_fps = frames_received_count / elapsed
                kbps = (total_bytes_count * 8) / (elapsed * 1024)
                print(
                    f"\r[GCS HUD] Video: {current_fps:.1f} FPS | Bitrate: {kbps:.1f} Kbps | "
                    f"Buffer: {len(active_frames)} frames",
                    end="",
                    flush=True
                )
                last_stat_time = now
                frames_received_count = 0
                total_bytes_count = 0

    except KeyboardInterrupt:
        print("\n\n[*] Receiver dihentikan oleh pengguna.")
    finally:
        sock.close()
        cv2.destroyAllWindows()
        print("[*] Socket ditutup. Selesai.")

if __name__ == "__main__":
    run_receiver()
