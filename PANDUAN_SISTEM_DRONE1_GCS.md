# Panduan Lengkap Sistem Monitoring Drone 1 (GCS, GPS, Video UDP, dan Telegram)

Dokumen ini berisi dokumentasi resmi, arsitektur jaringan, spesifikasi protokol, dan panduan operasional proyek **Monitoring Drone 1** untuk tugas Jaringan Komputer Lanjut.

---

## 1. Arsitektur dan Topologi Sistem

Sistem ini memisahkan jalur data **Video (Realtime UDP)** dan **GPS Telemetri (Datagram UDP)** agar performa transmisi tetap optimal dan tidak saling membebani:

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

## 2. Struktur Direktori Proyek

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
├── ipwebcam_to_udp_bridge.py      # Adapter zero-buffer IP Webcam -> UDP port 5002
├── telegram_bot.py                # Bot Telegram monitoring GCS
├── bot_config.json                # Konfigurasi token & chat_id (Aman / Diabaikan Git)
├── bot_config.json.example        # Template konfigurasi bot
├── test_gps_sender.py             # Script pengujian simulasi GPS lokal
└── .gitignore                     # Proteksi token dan cache agar tidak bocor
```

---

## 3. Spesifikasi Protokol Jaringan

### A. Protokol Video UDP (Port 5002)
* **Format Header Biner (8 Bytes, Network Byte Order `!IHH`):**
  - `frame_id` (`uint32` - 4 byte): Nomor urut unik setiap frame gambar.
  - `chunk_id` (`uint16` - 2 byte): Nomor indeks potongan frame (mulai dari `0`).
  - `total_chunks` (`uint16` - 2 byte): Jumlah potongan total dalam 1 frame utuh.
* **Payload:** Potongan citra JPEG dengan ukuran maksimal `1100 bytes` (Sangat aman dari fragmentasi karena jauh di bawah batas MTU standar 1500 bytes).
* **Low-Latency Engine:** Receiver menggunakan batas `FRAME_TIMEOUT = 0.2 detik` untuk segera membuang frame jika ada paket tercecer, menjaga video tetap sinkron tanpa lagging.

### B. Protokol GPS UDP (Port 5003)
* **Format:** JSON String UTF-8
* **Struktur Payload:**
  ```json
  {
    "device": "drone1",
    "lat": -6.184365,
    "lon": 106.779355,
    "accuracy_m": 14.5,
    "timestamp": "2026-10-28T10:00:00.000000+00:00"
  }
  ```
* **Stale Threshold:** Jika data tidak diperbarui dalam waktu **5.0 detik**, status otomatis beralih menjadi **DATA BASI / DISCONNECTED**.

---

## 4. Panduan Menjalankan Sistem untuk Demo / Pengujian

Pastikan Laptop GCS dan HP Android terhubung ke **jaringan Wi-Fi / Hotspot yang sama**.

### Langkah 1: Jalankan Komponen di Laptop (GCS)

Buka 4 terminal PowerShell di folder proyek:

* **Terminal 1 — Receiver GPS:**
  ```powershell
  python .\receiver\udp_gps_receiver.py
  ```
* **Terminal 2 — Receiver Video & OSD Telemetri:**
  ```powershell
  python .\receiver\udp_video_receiver.py
  ```
* **Terminal 3 — Bot Telegram:**
  ```powershell
  python telegram_bot.py
  ```
* **Terminal 4 — UDP Video Bridge:**
  ```powershell
  python ipwebcam_to_udp_bridge.py
  ```
  *(Ketikkan URL IP Webcam HP yang muncul di layar HP Anda lalu tekan Enter).*

---

### Langkah 2: Jalankan Komponen di HP Android (Drone 1)

1. **Kamera (IP Webcam):**
   - Buka aplikasi **IP Webcam**.
   - (Opsional rekomendasi) Atur resolusi ke `640x480` dan kualitas ke `50%` agar super cepat.
   - Scroll ke bawah dan tekan **Start server**.
2. **GPS (Termux):**
   - Buka aplikasi **Termux**.
   - Jalankan script GPS sender:
     ```bash
     python termux_gps_sender.py
     ```

---

## 5. Daftar Perintah Bot Telegram

Bot hanya merespons Chat ID yang terdaftar di `bot_config.json`:

| Perintah | Deskripsi |
| :--- | :--- |
| `/start` | Menampilkan pesan selamat datang, status otorisasi, dan daftar perintah. |
| `/status` | Menampilkan ringkasan status kesehatan Drone 1 (Online/Basi, IP pengirim, akurasi, waktu update). |
| `/gps` | Mengirimkan koordinat lokasi terkini (`Lat`, `Lon`), status data segar/basi, dan tautan langsung ke Google Maps. |
| `/photo` | Mengirimkan snapshot foto kamera drone terkini yang dilengkapi caption telemetri GPS realtime. |

---

## 6. Fitur Keamanan & Notifikasi Otomatis

* **Whitelist Chat ID:** Mencegah pihak luar memata-matai atau menyalahgunakan bot.
* **Token Protection:** Token bot disimpan di file lokal yang tidak masuk ke version control Git.
* **Alert Sinyal Terputus:** Jika GPS HP terputus lebih dari 5 detik, bot Telegram otomatis mengirimkan notifikasi darurat beserta koordinat terakhir drone (dengan *cooldown* 60 detik agar tidak spam).
* **Alert Pemulihan:** Saat sinyal tersambung kembali, bot memberi tahu pengguna bahwa sistem telah pulih.
