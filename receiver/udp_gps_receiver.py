import json
import socket
import time
from datetime import datetime, timezone

import os

# ============================================================
# KONFIGURASI RECEIVER GPS (GCS)
# ============================================================
LISTEN_IP = "0.0.0.0"           # 0.0.0.0 agar mendengarkan dari semua interface
LISTEN_PORT = 5003
STALE_THRESHOLD_SECONDS = 5.0  # Data > 5 detik dianggap basi

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LATEST_GPS_FILE = os.path.join(SCRIPT_DIR, "latest_gps.json")

def validate_gps_data(data):
    """
    Validasi kontrak data GPS sesuai AI_AGENT_RULES:
    - device: string non-kosong
    - lat: rentang -90 .. 90
    - lon: rentang -180 .. 180
    - accuracy_m: float/int non-negatif (opsional)
    - timestamp: string ISO 8601 valid
    """
    if not isinstance(data, dict):
        return False, "Payload bukan JSON objek/dictionary"

    device = data.get("device")
    if not device or not isinstance(device, str):
        return False, "Field 'device' tidak valid atau kosong"

    lat = data.get("lat")
    if not isinstance(lat, (int, float)) or not (-90.0 <= lat <= 90.0):
        return False, f"Field 'lat' ({lat}) di luar rentang -90..90"

    lon = data.get("lon")
    if not isinstance(lon, (int, float)) or not (-180.0 <= lon <= 180.0):
        return False, f"Field 'lon' ({lon}) di luar rentang -180..180"

    accuracy_m = data.get("accuracy_m")
    if accuracy_m is not None:
        if not isinstance(accuracy_m, (int, float)) or accuracy_m < 0:
            return False, f"Field 'accuracy_m' ({accuracy_m}) tidak valid (harus >= 0)"

    ts_str = data.get("timestamp")
    if not ts_str or not isinstance(ts_str, str):
        return False, "Field 'timestamp' tidak ditemukan"

    try:
        # Parsing ISO format (misal 2026-10-22T10:00:00Z)
        if ts_str.endswith("Z"):
            ts_str_clean = ts_str[:-1] + "+00:00"
        else:
            ts_str_clean = ts_str
        parsed_dt = datetime.fromisoformat(ts_str_clean)
    except Exception as e:
        return False, f"Format timestamp ISO 8601 tidak valid: {e}"

    return True, parsed_dt

def run_gps_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((LISTEN_IP, LISTEN_PORT))
    sock.settimeout(1.0)  # Timeout 1 detik agar loop tetap bisa memonitor status basi

    print("==================================================")
    print("      GCS GPS RECEIVER (DRONE 1 MONITOR)          ")
    print("==================================================")
    print(f"[*] Mendengarkan pada UDP {LISTEN_IP}:{LISTEN_PORT}")
    print(f"[*] Ambang batas data basi: > {STALE_THRESHOLD_SECONDS} detik")
    print("[*] Tekan CTRL+C untuk berhenti.\n")

    latest_data = None
    local_received_at = None

    try:
        while True:
            try:
                packet, addr = sock.recvfrom(2048)
                now = time.time()
                try:
                    payload_str = packet.decode("utf-8")
                    data = json.loads(payload_str)
                except Exception as e:
                    print(f"\n[!] Gagal decode JSON dari {addr}: {e}")
                    continue

                valid, result = validate_gps_data(data)
                if not valid:
                    print(f"\n[!] Data ditolak dari {addr}: {result}")
                    continue

                # Data valid
                local_received_at = now
                latest_data = {
                    "device": data["device"],
                    "lat": float(data["lat"]),
                    "lon": float(data["lon"]),
                    "accuracy_m": float(data.get("accuracy_m", 0.0)) if data.get("accuracy_m") is not None else None,
                    "device_timestamp": data["timestamp"],
                    "local_received_at": local_received_at,
                    "sender_ip": addr[0],
                    "sender_port": addr[1],
                    "is_stale": False
                }

                # Simpan ke file cache status untuk dipakai bot Telegram (Tahap 2)
                try:
                    with open(LATEST_GPS_FILE, "w") as f:
                        json.dump(latest_data, f, indent=2)
                except Exception:
                    pass

                acc_str = f"{latest_data['accuracy_m']:.1f}m" if latest_data['accuracy_m'] is not None else "N/A"
                print(
                    f"\r[GPS SEGAR] Device: {latest_data['device']} | "
                    f"Lat: {latest_data['lat']:.6f}, Lon: {latest_data['lon']:.6f} | "
                    f"Acc: {acc_str} | Waktu Lokal: {time.strftime('%H:%M:%S', time.localtime(local_received_at))}",
                    end="",
                    flush=True
                )

            except socket.timeout:
                # Periksa apakah data terakhir sudah basi
                if latest_data is not None and local_received_at is not None:
                    age = time.time() - local_received_at
                    if age > STALE_THRESHOLD_SECONDS:
                        latest_data["is_stale"] = True
                        try:
                            with open(LATEST_GPS_FILE, "w") as f:
                                json.dump(latest_data, f, indent=2)
                        except Exception:
                            pass

                        print(
                            f"\r[GPS BASI/TIMEOUT] Device: {latest_data['device']} | "
                            f"Terakhir {age:.1f}s lalu | Status: SIGNAL LOST/DISCONNECTED      ",
                            end="",
                            flush=True
                        )

    except KeyboardInterrupt:
        print("\n\n[*] Receiver GPS dihentikan oleh pengguna.")
    finally:
        sock.close()
        print("[*] Socket GPS ditutup.")

if __name__ == "__main__":
    run_gps_receiver()
