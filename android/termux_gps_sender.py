#!/usr/bin/env python3
"""
Script pengirim GPS dari HP Android (Termux) ke Laptop GCS via UDP.
Membutuhkan:
1. Termux App & Termux:API App (dari F-Droid)
2. Di dalam Termux jalankan:
   pkg install python termux-api
   pip install requests (opsional)
"""

import subprocess
import json
import socket
import time
from datetime import datetime, timezone

# ============================================================
# KONFIGURASI PENGIRIM GPS ANDROID
# ============================================================
GCS_IP = "10.90.33.15"       # Sesuaikan dengan IP Wi-Fi Laptop GCS
GCS_PORT = 5003
DEVICE_NAME = "drone1"
SEND_INTERVAL_SECONDS = 1.0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def get_termux_gps():
    """
    Mengambil data lokasi dari sensor Android via Termux API.
    Urutan strategi:
    1. GPS satelit posisi terakhir (-p gps -r last) -> cepat jika drone di luar ruangan.
    2. Network posisi terakhir (-p network -r last) -> cepat jika di dalam ruangan / cache ada.
    3. Network pengambilan baru (-p network -r once) -> fallback jika cache kosong.
    """
    attempts = [
        ["termux-location", "-p", "gps", "-r", "last"],
        ["termux-location", "-p", "network", "-r", "last"],
        ["termux-location", "-p", "network", "-r", "once"],
    ]

    for cmd in attempts:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2.0
            )
            if proc.returncode == 0 and proc.stdout.strip():
                raw = json.loads(proc.stdout)
                if "latitude" in raw and "longitude" in raw:
                    return raw
        except subprocess.TimeoutExpired:
            continue
        except Exception as e:
            continue
    return None

def main():
    print("==========================================")
    print(f" ANDROID GPS SENDER -> {GCS_IP}:{GCS_PORT}")
    print("==========================================")
    print("Pastikan GPS HP aktif & izin Termux:API diberikan.")
    print("Tekan CTRL+C untuk berhenti.\n")

    while True:
        gps_data = get_termux_gps()

        if gps_data and "latitude" in gps_data and "longitude" in gps_data:
            payload = {
                "device": DEVICE_NAME,
                "lat": float(gps_data["latitude"]),
                "lon": float(gps_data["longitude"]),
                "accuracy_m": float(gps_data.get("accuracy", 0.0)),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            msg = json.dumps(payload).encode("utf-8")
            sock.sendto(msg, (GCS_IP, GCS_PORT))
            print(f"[OK] Terkirim: Lat={payload['lat']}, Lon={payload['lon']} (Acc: {payload['accuracy_m']}m)")
        else:
            print("[WAIT] Menunggu fix sinyal GPS dari sensor Android...")

        time.sleep(SEND_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDihentikan.")
    finally:
        sock.close()
