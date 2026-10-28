# Drone 1 — Ground Control Station (GCS) System
> **Real-Time UDP Video Streaming, GPS Telemetry, OSD HUD, Face Recognition, and Telegram Bot Monitoring.**  
> Proyek Akhir Mata Kuliah Jaringan Komputer Lanjut.

---

## 🚀 Fitur Utama

- **Jalur Video Realtime Rendah Latensi (UDP Port 5002):**
  - Menggunakan socket UDP kustom dengan pemecahan paket biner (*chunking*) maksimal 1100 bytes (jauh di bawah MTU 1500) ber-header `!IHH` (8 bytes).
  - Dilengkapi *Zero-Buffer Frame Reader* yang memangkas latensi video dari ~1.5 detik menjadi **< 100 ms (nyaris instan)**.
- **Jalur Telemetri GPS Berkala (UDP Port 5003):**
  - Menerima koordinat sensor HP Android nyata (via Termux API) secara terpisah dari jalur video.
  - Validasi koordinat otomatis dan deteksi status data basi (*stale threshold* 5.0 detik).
- **On-Screen Display (OSD / HUD) Telemetri di Layar GCS:**
  - Menampilkan status konektivitas drone (`ONLINE` / `GPS BASI`), nilai FPS, koordinat lintang/bujur (`LAT`, `LON`), akurasi sensor, dan usia pembaruan data secara langsung di atas video.
- **Face Recognition AI (LBPH Classifier):**
  - Mengenali 2 orang target (menampilkan bounding box **HIJAU** + Nama + Persentase Kemiripan).
  - Secara otomatis menolak orang lain / orang asing dengan bounding box **MERAH** bertuliskan **`[UNKNOWN]`**.
  - Waktu pelatihan model super cepat (~3 detik).
- **Bot Monitoring Telegram Terotorisasi:**
  - Pembatasan akses berbasis *Whitelist Chat ID* (menolak akses dari pihak tidak sah).
  - Perintah lengkap: `/start`, `/status`, `/gps`, dan `/photo` (mengirim snapshot foto kamera drone terkini beserta caption koordinat Google Maps).
  - *Asynchronous Background Alert:* Mengirim notifikasi darurat otomatis saat drone kehilangan sinyal (dilengkapi cooldown 60 detik agar tidak spam).

---

## 🏗️ Arsitektur Sistem

```text
[ HP Android (Drone 1 Node) ]
├── 1. Kamera (Aplikasi IP Webcam)
│      └── HTTP MJPEG Stream (WiFi LAN)
│
└── 2. GPS Sensor (Termux API)
       └── termux_gps_sender.py ──(UDP Port 5003)──┐
                                                   │
Jaringan Wi-Fi / Hotspot Bersama                   │
                                                   ▼
[ Laptop GCS (Ground Control Station) ] ───────────┘
├── A. ipwebcam_to_udp_bridge.py
│      └── Menerima HTTP stream -> Memotong frame JPEG menjadi chunk UDP (< MTU 1100 byte)
│          dengan header biner '!IHH' (8 bytes) ──(UDP Port 5002)──┐
│                                                                  │
├── B. udp_video_receiver.py ◄─────────────────────────────────────┘
│      ├── Menerima & merakit chunk UDP (Port 5002)
│      ├── Membaca cache GPS (latest_gps.json)
│      ├── Merender OSD / HUD Telemetri di atas video
│      ├── Mendeteksi wajah & label nama / [UNKNOWN]
│      └── Menyimpan snapshot terkini (latest_frame.jpg)
│
├── C. udp_gps_receiver.py
│      ├── Menerima payload JSON koordinat (Port 5003)
│      ├── Validasi rentang (-90..90, -180..180) & status data basi (> 5 detik)
│      └── Menyimpan status ke latest_gps.json
│
└── D. telegram_bot.py
       ├── Terhubung ke Telegram API via polling
       ├── Pembatasan akses aman (Whitelist Chat ID)
       ├── Menangani /start, /status, /gps, /photo
       └── Background Alert Monitor (Peringatan putus sinyal dengan cooldown 60s)
```

---

## 📋 Struktur Direktori Proyek

```text
Jarkom_lanjut/
├── android/
│   └── termux_gps_sender.py       # Script pengirim GPS dari HP Android (Termux)
├── receiver/
│   ├── udp_video_receiver.py      # Receiver video UDP + HUD Telemetri GCS
│   ├── udp_gps_receiver.py        # Receiver koordinat GPS UDP
│   ├── latest_gps.json            # Cache status GPS realtime/stale
│   ├── latest_frame.jpg           # Snapshot foto kamera drone terkini
│   └── PENJELASAN.md              # Spesifikasi teknis protokol video chunking
├── dataset/
│   ├── orang_1/                   # Folder foto wajah target 1
│   ├── orang_2/                   # Folder foto wajah target 2
│   └── PETUNJUK_UNTUK_TEMAN.txt   # Panduan pengumpulan dataset
├── models/
│   ├── haarcascade_frontalface_default.xml # Cascade deteksi wajah
│   ├── face_recognizer.xml        # Model hasil training LBPH
│   └── labels.json                # Mapping ID label ke nama orang
├── ipwebcam_to_udp_bridge.py      # Adapter zero-buffer IP Webcam -> UDP port 5002
├── telegram_bot.py                # Bot Telegram monitoring GCS
├── collect_photos.py              # Tool pengumpul foto dataset via webcam
├── train_faces.py                 # Script pelatihan model wajah instan
├── bot_config.json.example        # Template konfigurasi bot aman
├── test_gps_sender.py             # Script pengujian simulasi GPS lokal
├── laporan.md                     # Laporan akademik resmi tugas akhir
├── PANDUAN_SISTEM_DRONE1_GCS.md   # Panduan operasional demo lengkap
└── .gitignore                     # Proteksi token dan cache agar tidak bocor
```

---

## ⚙️ Persyaratan Sistem

### Di Laptop (GCS Windows / Linux):
- Python 3.10+ (disarankan Python 3.12 atau 3.13)
- Library Python:
  ```powershell
  pip install opencv-python opencv-contrib-python numpy python-telegram-bot
  ```

### Di HP Android (Node Drone 1):
1. **Aplikasi IP Webcam** (Download gratis dari Google Play Store oleh *Pavel Khlebovich*).
2. **Aplikasi Termux** & **Termux:API** (disarankan dari F-Droid).
   - Di dalam terminal Termux, install dependensi:
     ```bash
     pkg update -y && pkg install python termux-api -y
     ```

---

## 🚀 Panduan Menjalankan Sistem

Pastikan Laptop GCS dan HP Android terhubung ke **jaringan Wi-Fi / Hotspot yang sama**.

### 1. Konfigurasi Bot Telegram (Sekali Saja)
Salin file `bot_config.json.example` menjadi `bot_config.json`:
```json
{
  "bot_token": "MASUKKAN_TOKEN_BOT_DARI_BOTFATHER",
  "allowed_chat_ids": [
    123456789
  ]
}
```
*(Catatan: `bot_config.json` sudah diabaikan oleh `.gitignore` sehingga token Anda aman dan tidak akan bocor ke GitHub).*

---

### 2. Jalankan Komponen di Laptop (GCS)
Buka terminal PowerShell terpisah untuk masing-masing modul:

- **Terminal 1 — Receiver GPS:**
  ```powershell
  python .\receiver\udp_gps_receiver.py
  ```
- **Terminal 2 — Receiver Video & Telemetri HUD:**
  ```powershell
  python .\receiver\udp_video_receiver.py
  ```
- **Terminal 3 — Bot Telegram Monitoring:**
  ```powershell
  python telegram_bot.py
  ```
- **Terminal 4 — Bridge Video UDP:**
  ```powershell
  python ipwebcam_to_udp_bridge.py
  ```
  *(Masukkan URL IP Webcam yang tertera pada layar HP Anda, misal: `http://10.90.32.215:8080/video`).*

---

### 3. Jalankan Pengirim di HP Android (Drone 1)
1. **Nyalakan Kamera (IP Webcam):**
   - Buka aplikasi **IP Webcam**.
   - (Rekomendasi) Ubah resolusi video ke `640x480` dan kualitas ke `50%` agar streaming sangat cepat.
   - Scroll ke menu paling bawah lalu tekan **Start server**.
2. **Nyalakan GPS (Termux):**
   - Buka aplikasi **Termux**.
   - Jalankan script pengirim GPS:
     ```bash
     python termux_gps_sender.py
     ```

---

## 🧑‍🤝‍🧑 Panduan Pelatihan Dataset Wajah (Face Recognition)

1. Kumpulkan 15–20 foto wajah dari 2 orang target. Masukkan ke dalam folder:
   - `dataset/Nama_Orang_1/` (contoh: `dataset/Ardi/`)
   - `dataset/Nama_Orang_2/` (contoh: `dataset/Shaqil/`)
   *(Atau gunakan tool `python collect_photos.py` untuk memotret via webcam)*.
2. Jalankan pelatihan model (hanya butuh 3 detik):
   ```powershell
   python train_faces.py
   ```
3. Begitu selesai, jalankan kembali `udp_video_receiver.py`. Layar GCS akan otomatis:
   - Menampilkan bounding box **HIJAU** + Nama jika wajah yang terdaftar terdeteksi.
   - Menampilkan bounding box **MERAH** bertuliskan **`[UNKNOWN]`** jika ada orang lain atau orang asing yang masuk kamera!

---

## 📱 Daftar Perintah Bot Telegram

| Perintah | Deskripsi |
| :--- | :--- |
| `/start` | Salam pembuka dan status verifikasi akses pengguna. |
| `/status` | Ringkasan kesehatan drone (Online/Basi, IP pengirim, akurasi, waktu update). |
| `/gps` | Koordinat GPS terkini (`Lat`, `Lon`) beserta link Google Maps langsung. |
| `/photo` | Mengirim snapshot foto kamera drone terkini lengkap dengan caption telemetri GPS. |

---

## 📄 Laporan Proyek Lengkap

Laporan akademik resmi proyek ini dengan analisis teknis mendalam tersedia di file [laporan.md](laporan.md).

---

## 👥 Pengembang
- **Kelompok:** Drone 1 GCS Team
- **Mata Kuliah:** Jaringan Komputer Lanjut
- **Repository:** [https://github.com/YooowwMann/Jaringan_komputer_lanjut.git](https://github.com/YooowwMann/Jaringan_komputer_lanjut.git)
