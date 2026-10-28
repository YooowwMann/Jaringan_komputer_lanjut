import socket
import json
import time
from datetime import datetime, timezone

# ============================================================
# TEST GPS SENDER (Untuk Simulasi / Uji Coba Koneksi Lokal)
# ============================================================
GCS_IP = "127.0.0.1"        # Ganti dengan IP Wi-Fi GCS jika dites dari perangkat lain
GCS_PORT = 5003

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"[*] Mengirim 5 paket data GPS uji ke {GCS_IP}:{GCS_PORT}...")

# Contoh koordinat awal
lat = -6.200000
lon = 106.816666

for i in range(5):
    # Simulasi pergerakan kecil
    current_lat = lat + (i * 0.0001)
    current_lon = lon + (i * 0.0001)
    
    payload = {
        "device": "drone1",
        "lat": round(current_lat, 6),
        "lon": round(current_lon, 6),
        "accuracy_m": 4.5,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    raw_data = json.dumps(payload).encode("utf-8")
    sock.sendto(raw_data, (GCS_IP, GCS_PORT))
    print(f"[{i+1}/5] Terkirim: {payload}")
    time.sleep(1)

print("\n[*] 5 paket selesai dikirim.")
print("[*] Berhenti mengirim selama 7 detik untuk menguji timeout/status data BASI...")
time.sleep(7)

print("[*] Selesai pengujian.")
sock.close()
