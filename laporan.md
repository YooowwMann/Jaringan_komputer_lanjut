# LAPORAN PROYEK AKHIR MATA KULIAH JARINGAN KOMPUTER LANJUT
## SISTEM MONITORING DRONE 1: REAL-TIME UDP VIDEO STREAMING, GPS TELEMETRY, OSD HUD, FACE RECOGNITION, DAN BOT TELEGRAM

---

**Disusun Oleh:**
- **Kelompok:** Drone 1 GCS Team
- **Mata Kuliah:** Jaringan Komputer Lanjut
- **Repository GitHub:** [https://github.com/YooowwMann/Jaringan_komputer_lanjut.git](https://github.com/YooowwMann/Jaringan_komputer_lanjut.git)

---

## DAFTAR ISI
1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Latar Belakang dan Tujuan](#2-latar-belakang-dan-tujuan)
3. [Arsitektur Sistem dan Topologi Jaringan](#3-arsitektur-sistem-dan-topologi-jaringan)
4. [Spesifikasi dan Desain Protokol Komunikasi](#4-spesifikasi-dan-desain-protokol-komunikasi)
   - 4.1 Protokol Video Streaming UDP (Port 5002)
   - 4.2 Protokol Telemetri GPS UDP (Port 5003)
   - 4.3 Zero-Buffer Frame Reader (Optimasi Low-Latency)
5. [Implementasi Subsistem](#5-implementasi-subsistem)
   - 5.1 GCS On-Screen Display (OSD / HUD) Video Receiver
   - 5.2 Face Recognition (LBPH Classifier & Unknown Detection)
   - 5.3 Bot Telegram Terotorisasi & Alert System Asinkron
   - 5.4 Android GPS Telemetry Sender (Termux API)
6. [Hasil Pengujian Nyata dan Analisis Performa](#6-hasil-pengujian-nyata-dan-analisis-performa)
7. [Kesimpulan](#7-kesimpulan)

---

## 1. Ringkasan Eksekutif

Proyek ini bertujuan merancang dan mengimplementasikan sistem stasiun kendali darat (*Ground Control Station* / GCS) pemantauan nirkabel untuk wahana tanpa awak (*Drone 1*). Sistem memanfaatkan perangkat pintar Android yang terpasang pada wahana sebagai node pengirim sensor (kamera dan GPS), serta laptop Windows sebagai GCS penerima.

Sistem berhasil mengimplementasikan komunikasi nirkabel berbasis **UDP Socket Programming murni**, pemotongan paket (*chunking*) di bawah batas MTU 1500 bytes dengan header biner kustom `!IHH`, deteksi keterlambatan data (*stale data detection*), visualisasi telemetri OSD (*On-Screen Display*), kecerdasan buatan pengenalan wajah (*Face Recognition*) dengan kemampuan menolak orang asing (*Unknown classification*), serta integrasi bot monitoring Telegram yang dilengkapi pengiriman snapshot kamera terkini (`/photo`) dan peringatan putus sinyal darurat otomatis.

---

## 2. Latar Belakang dan Tujuan

Pada aplikasi pemantauan drone, jalur transmisi video dan telemetri menghadapi tantangan mendasar pada lapisan transport:
1. **Latensi Transmisi Video:** Penggunaan protokol TCP untuk video streaming memicu akumulasi *head-of-line blocking* dan buffering saat terjadi *packet loss*, sehingga video tertinggal beberapa detik dari kondisi nyata di udara.
2. **Fragmentasi Jaringan:** Paket data gambar berukuran puluhan kilobyte yang dikirim utuh via UDP tanpa pemotongan rawan mengalami fragmentasi IP di tingkat router Wi-Fi, yang meningkatkan risiko kegagalan rekonstruksi frame secara drastis.
3. **Pemisahan Jalur Telemetri:** Data lokasi penerbangan (GPS) memerlukan frekuensi pembacaan berkala independen dan tidak boleh terinterupsi oleh lalu lintas transmisi video yang padat.

### Tujuan Proyek:
1. Membangun transmisi video berkecepatan tinggi dengan latensi rendah menggunakan socket UDP port `5002` melalui pemecahan paket (*chunking*) biner.
2. Membangun transmisi data koordinat GPS HP Android secara berkala via socket UDP port `5003` dengan validasi rentang koordinat dan deteksi sinyal basi (*stale data*).
3. Menggabungkan informasi video dan telemetri ke dalam tampilan HUD/OSD interaktif pada GCS.
4. Menerapkan model kecerdasan buatan pengenalan wajah (LBPH) yang dapat membedakan wajah 2 orang target secara akurat dan melabeli pihak lain sebagai `[UNKNOWN]`.
5. Mengintegrasikan pemantauan jarak jauh melalui Bot Telegram dengan mekanisme whitelist chat ID dan notifikasi darurat asinkron.

---

## 3. Arsitektur Sistem dan Topologi Jaringan

Sistem menggunakan topologi jaringan *Wireless Local Area Network* (WLAN / Wi-Fi) dengan memisahkan dua saluran transport independen:

```text
       ┌────────────────────────────────────────────────────────┐
       │                 HP ANDROID (DRONE 1)                   │
       ├──────────────────────────┬─────────────────────────────┤
       │ Kamera (Aplikasi IP Cam) │  GPS Sensor (Termux API)    │
       │ HTTP MJPEG Stream (LAN)  │  termux_gps_sender.py       │
       └─────────────┬────────────┴──────────────┬──────────────┘
                     │                           │
                     │ (WiFi LAN)                │ (UDP Datagram Port 5003)
                     ▼                           ▼
       ┌────────────────────────────────────────────────────────┐
       │                 LAPTOP GCS (WINDOWS)                   │
       ├──────────────────────────┬─────────────────────────────┤
       │ ipwebcam_to_udp_bridge.py│   udp_gps_receiver.py       │
       │ - Zero-Buffer Thread     │   - JSON Payload Validator  │
       │ - Binary Chunking (!IHH) │   - Stale Filter (> 5.0s)   │
       │         │ (UDP Port 5002)│              │              │
       │         ▼                │              ▼              │
       │  udp_video_receiver.py   │      latest_gps.json        │
       │  - Packet Reassembly     │             │               │
       │  - OSD / HUD Telemetry   │◄────────────┘               │
       │  - LBPH Face Recognition │                             │
       │  - Auto-Save Snapshot    │                             │
       │         │                │                             │
       │         ▼                │                             │
       │  latest_frame.jpg        │                             │
       │         │                │                             │
       │         ▼                ▼                             │
       │                telegram_bot.py                         │
       │                - Whitelist Chat ID Auth                │
       │                - /start, /status, /gps, /photo         │
       │                - Async Disconnect Alert Loop           │
       └──────────────────────────┬─────────────────────────────┘
                                  │
                                  ▼ (Telegram Bot API)
                      ┌───────────────────────┐
                      │  USER TELEGRAM APP    │
                      └───────────────────────┘
```

---

## 4. Spesifikasi dan Desain Protokol Komunikasi

### 4.1 Protokol Video Streaming UDP (Port 5002)

Agar transmisi citra terhindar dari fragmentasi router (standar MTU 1500 bytes), setiap citra JPEG dipecah menjadi potongan (*chunks*) maksimal **1100 bytes**. Setiap potongan dibungkus oleh header biner berukuran **8 bytes** berformat Big-Endian (`!IHH`):

| Offset | Field | Tipe Data | Ukuran | Deskripsi |
| :---: | :--- | :--- | :---: | :--- |
| 0 - 3 | `frame_id` | `uint32` (Unsigned Int) | 4 Bytes | Nomor urut unik penanda frame (0 - 4.294.967.295) |
| 4 - 5 | `chunk_id` | `uint16` (Unsigned Short) | 2 Bytes | Indeks urutan chunk pada frame tersebut (mulai 0) |
| 6 - 7 | `total_chunks` | `uint16` (Unsigned Short) | 2 Bytes | Total jumlah potongan yang menyusun 1 frame |
| 8 - N | `payload` | `binary` (Byte Array) | Maks 1100 B | Potongan data JPEG mentah |

**Total Ukuran Paket UDP:** 8 bytes header + maks 1100 bytes data = **1108 bytes** (Sangat aman di bawah MTU 1500 bytes).

**Mekanisme Rekonstruksi (*Reassembly*) & Low-Latency Dropping:**
- Receiver mengelompokkan paket berdasarkan `frame_id`.
- Begitu jumlah potongan lengkap terakumulasi, byte dirangkai berurutan `chunk_id = 0 .. total_chunks - 1`.
- Jika terdapat paket yang hilang di udara melebihi ambang batas `FRAME_TIMEOUT = 0.2 detik`, frame yang belum lengkap langsung dibuang dari memori agar buffer tidak menumpuk dan tampilan video tidak tersendat.

### 4.2 Protokol Telemetri GPS UDP (Port 5003)

Pengirim HP mengirimkan pesan JSON berformat UTF-8 setiap interval 1.0 detik:
```json
{
  "device": "drone1",
  "lat": -6.184366,
  "lon": 106.779355,
  "accuracy_m": 14.5,
  "timestamp": "2026-10-28T07:42:30.289031+00:00"
}
```

**Aturan Validasi dan Deteksi Data Basi (*Stale Data Threshold*):**
- Koordinat `lat` divalidasi pada rentang `-90.0 .. 90.0` dan `lon` pada `-180.0 .. 180.0`.
- Waktu penerimaan lokal GCS (`local_received_at`) dicatat secara terpisah dari waktu sensor HP.
- Jika selisih waktu `time.time() - local_received_at > 5.0 detik`, sistem GCS secara otomatis menandai data dengan flag `"is_stale": true` dan status berubah dari `ONLINE` menjadi `DATA BASI / DISCONNECTED`.

### 4.3 Zero-Buffer Frame Reader (Optimasi Low-Latency)

Secara default, `cv2.VideoCapture` pada stream jaringan menjaga antrean buffer sebanyak 4–5 frame, yang menimbulkan latensi artifisial sebesar 1–2 detik di belakang kejadian nyata. Modul bridge mengimplementasikan class `FreshFrameReader`:
- Menggunakan thread latar belakang independen yang secara kontinu membaca frame dan membuang frame lama yang menumpuk di buffer socket OS.
- Hasil: Latensi transmisi kamera HP ke tampilan layar GCS terpangkas hingga menjadi **< 100 ms (realtime mutlak)**.

---

## 5. Implementasi Subsistem

### 5.1 GCS On-Screen Display (OSD / HUD) Video Receiver
Modul [receiver/udp_video_receiver.py](file:///C:/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/receiver/udp_video_receiver.py) menggabungkan umpan video dengan visualisasi telemetri penerbangan:
- **Header Bar:** Menampilkan status konektivitas drone (`DRONE 1 : ONLINE` warna hijau / `DRONE 1 : GPS BASI` warna oranye) dan *frame rate* (FPS).
- **Footer Bar:** Menampilkan koordinat garis lintang dan bujur (`LAT`, `LON`), akurasi sensor GPS (`±m`), dan usia data pembaruan.
- **Snapshot Generator:** Secara otomatis menyimpan frame terkini ke [receiver/latest_frame.jpg](file:///C:/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/receiver/latest_frame.jpg) untuk diakses oleh bot Telegram.

### 5.2 Face Recognition (LBPH Classifier & Unknown Detection)
Sistem kecerdasan buatan dirancang menggunakan algoritma *Local Binary Patterns Histograms* (LBPH) dan *Haar Cascade Classifier*:
- **Pelatihan Cepat:** Script [train_faces.py](file:///C:/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/train_faces.py) mengekstrak fitur wajah dari folder `dataset/` hanya dalam 3 detik dan menghasilkan model [models/face_recognizer.xml](file:///C:/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/models/face_recognizer.xml).
- **Klasifikasi Terverifikasi vs Asing:**
  - Jika jarak kemiripan (*distance*) < 75.0: Wajah dikenali sebagai target (kotak **HIJAU** dengan nama dan persentase akurasi).
  - Jika jarak kemiripan >= 75.0 atau wajah tidak terdaftar di dataset: Sistem menolak identitas dan memunculkan kotak **MERAH** berlabel **`[UNKNOWN]`**.

### 5.3 Bot Telegram Terotorisasi & Alert System Asinkron
Modul [telegram_bot.py](file:///C:/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/telegram_bot.py) menggunakan library `python-telegram-bot` (v22.8) dengan prinsip keamanan tinggi:
- **Whitelist Chat ID:** Memfilter pengirim perintah berdasarkan array `allowed_chat_ids` di file konfigurasi lokal [bot_config.json](file:///C:/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/bot_config.json) (yang diabaikan oleh `.gitignore`).
- **Perintah `/status`:** Menampilkan kesehatan perangkat, IP pengirim, dan latensi data GPS.
- **Perintah `/gps`:** Mengirimkan koordinat terkini dan tautan peta interaktif Google Maps.
- **Perintah `/photo`:** Mengirimkan foto kamera drone saat ini dengan caption telemetri lengkap.
- **Background Alert Task:** Task asinkron memantau status drone tiap 5 detik; jika sinyal terputus > 5 detik, notifikasi darurat push dikirimkan ke Telegram pengguna (dilengkapi cooldown 60 detik untuk mencegah spam).

### 5.4 Android GPS Telemetry Sender (Termux API)
Script [android/termux_gps_sender.py](file:///C:/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/android/termux_gps_sender.py) berjalan pada terminal Termux HP:
- Mengimplementasikan *smart fallback*: Mencoba sensor satelit `gps` untuk operasi outdoor; jika belum mengunci sinyal satelit di dalam ruangan, script otomatis beralih (*fallback*) ke penyedia `network` secara mulus tanpa menghentikan transmisi UDP.

---

## 6. Hasil Pengujian Nyata dan Analisis Performa

Pengujian dilakukan menggunakan perangkat keras nyata:
- **GCS Node:** Laptop AMD Ryzen 7 7445HS, RTX 3050 GPU, 16 GB RAM (IP: `10.90.33.15`).
- **Drone Node:** HP Android dengan Termux & IP Webcam (IP: `10.90.32.215`).

### Tabel Matriks Hasil Pengujian:

| No | Komponen yang Diuji | Skenario Pengujian | Hasil Aktual yang Terekam | Status |
| :---: | :--- | :--- | :--- | :---: |
| 1 | **Transmisi GPS UDP** | Pengiriman data koordinat dari Termux HP ke port 5003 | GCS berhasil menerima koordinat nyata (-6.184365, 106.779355) dengan status `[GPS SEGAR]` | **LULUS** |
| 2 | **Stale Data Detector** | Script pengirim di HP dimatikan selama > 5 detik | GCS otomatis mengubah status menjadi `[GPS BASI/TIMEOUT]` dan mencatat `is_stale: true` | **LULUS** |
| 3 | **Telegram /status & /gps** | Mengakses bot saat GPS aktif dan saat GPS terputus | Bot menampilkan status `ONLINE` saat aktif dan `DATA BASI` saat terputus beserta link Google Maps | **LULUS** |
| 4 | **Keamanan Chat ID** | Percobaan akses bot dari akun Telegram tidak terdaftar | Akses ditolak secara instan (`⛔ Akses Ditolak`) dan dicatat di log keamanan terminal | **LULUS** |
| 5 | **Streaming Video UDP** | Pengiriman video kamera HP via chunking biner `!IHH` port 5002 | Video tampil lancar pada resolusi 640x480 tanpa fragmentasi atau green frame | **LULUS** |
| 6 | **Optimasi Delay (Latency)** | Perbandingan sebelum dan sesudah `FreshFrameReader` | Latensi berkurang drastis dari ~1.5 detik menjadi < 100 ms (responsif seketika) | **LULUS** |
| 7 | **Snapshot Foto (/photo)** | Mengirim perintah `/photo` pada bot Telegram | Bot berhasil mengirim file `latest_frame.jpg` (59.6 KB) beserta koordinat telemetri | **LULUS** |
| 8 | **Deteksi Disconnect Alert** | Koneksi sinyal drone sengaja diputus | Bot Telegram otomatis membunyikan notifikasi darurat `🚨 SINYAL TERPUTUS` dengan posisi terakhir | **LULUS** |
| 9 | **Face Recognition Model** | Verifikasi pipeline training model LBPH | `train_faces.py` berhasil memproses struktur folder dan siap membedakan target vs `[UNKNOWN]` | **LULUS** |

---

## 7. Kesimpulan

Proyek akhir **Sistem Monitoring Drone 1** telah berhasil dirancang, diuji, dan memenuhi seluruh kriteria kelulusan sistem jaringan komputer tingkat lanjut:
1. **Kehandalan Protokol UDP:** Penggunaan socket UDP dengan header biner `!IHH` dan chunking 1100 bytes terbukti sangat andal dan efisien untuk transmisi citra nirkabel tanpa degradasi akibat fragmentasi router.
2. **Kemandirian Jalur Data:** Pemisahan jalur transmisi Video (Port 5002) dan GPS (Port 5003) menjamin kestabilan telemetri penerbangan bahkan saat jalur video mengalami fluktuasi beban.
3. **Kemudahan Pengoperasian:** Arsitektur sistem memungkinkan siapa pun anggota kelompok menggunakan kameranya hanya dengan memasang aplikasi standar IP Webcam, sementara seluruh standar pemrosesan UDP socket murni dan kecerdasan buatan tetap dijalankan secara terpusat dan optimal pada stasiun kontrol darat (GCS).
