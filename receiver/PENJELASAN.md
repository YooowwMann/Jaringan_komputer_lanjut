# Dokumentasi dan Spesifikasi: UDP Video Receiver (GCS)

Dokumen ini menjelaskan rancangan, struktur protokol, dan tata cara penggunaan modul **UDP Video Receiver** untuk stasiun kontrol darat (Ground Control Station / GCS).

---

## 1. Peran dan Arsitektur

Modul [udp_video_receiver.py](file:///C:/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/receiver/udp_video_receiver.py) bertugas sebagai penerima stream video real-time dari pengirim (Drone 1 / HP Android).

```text
[ HP Android / Drone 1 ] 
       │ (CameraX / MJPG Capture)
       │ (JPEG Encode @ Q60)
       │ (Pemecahan per 1100 bytes + Header !IHH)
       ▼ UDP Port 5002
[ GCS Receiver (udp_video_receiver.py) ]
       ├── 1. Baca paket socket UDP (recvfrom)
       ├── 2. Ekstrak Header '!IHH' (frame_id, chunk_id, total_chunks)
       ├── 3. Rekonstruksi & Susun Chunk (Reassembly buffer)
       ├── 4. Decode JPEG (cv2.imdecode)
       └── 5. Render Video Window (cv2.imshow)
```

---

## 2. Kontrak Protokol Paket UDP

Agar paket video tidak mengalami pemotongan (*fragmentation*) yang tidak terduga di lapisan router jaringan Wi-Fi, pengirim memecah (*chunk*) data JPEG menjadi bagian kecil di bawah batas standar MTU (1500 bytes).

### Struktur Header Biner (8 Bytes)
Format `struct`: `!IHH` (Network Byte Order / Big-Endian)

| Field | Tipe Data C | Ukuran | Deskripsi |
| :--- | :--- | :--- | :--- |
| `frame_id` | `unsigned int` (uint32) | 4 bytes | ID unik penomoran frame (0 – 4.294.967.295) |
| `chunk_id` | `unsigned short` (uint16) | 2 bytes | Nomor urut chunk untuk frame ini (mulai dari 0) |
| `total_chunks` | `unsigned short` (uint16) | 2 bytes | Total jumlah chunk yang membentuk 1 frame utuh |

### Spesifikasi Payload
* **Ukuran Chunk (`CHUNK_SIZE`)**: `1100 bytes` (maksimum payload per paket).
* **Total Ukuran Paket UDP**: Header (8 bytes) + Payload (maks 1100 bytes) = **1108 bytes** (Sangat aman, jauh di bawah MTU 1500 bytes).
* **Format Gambar**: Kompresi citra JPEG (`.jpg`).

---

## 3. Logika Rekonstruksi (*Reassembly*) & Penanganan Paket Hilang

Protokol UDP bersifat *unreliable* (paket bisa tiba tidak berurutan atau hilang di udara):
1. **Penyimpanan Dinamis**: Setiap paket yang masuk dikelompokkan ke kamus berdasarkan `frame_id`.
2. **Kelengkapan**: Ketika jumlah chunk yang diterima sama dengan `total_chunks`, chunk digabungkan secara berurutan `chunk_id = 0, 1, ..., total_chunks - 1`.
3. **Timeout Kadaluarsa (`FRAME_TIMEOUT = 0.5s`)**: Jika ada salah satu paket hilang dalam transmisi nirkabel sehingga frame tidak lengkap, buffer frame tersebut akan dibersihkan agar memori tidak bocor dan tidak menimbulkan *lag*.

---

## 4. Cara Menjalankan

### A. Dijalankan di Windows (Direkomendasikan untuk Tampilan GUI Lancar)
Buka terminal PowerShell pada folder ini:
```powershell
python .\receiver\udp_video_receiver.py
```

### B. Dijalankan di WSL2 (Ubuntu 24.04)
Jika dijalankan di dalam WSL:
```bash
python3 /mnt/c/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/receiver/udp_video_receiver.py
```
> [!NOTE]
> Jika WSL2 Anda belum memiliki server X11/Wayland (WSLg) aktif atau mengalami kendala tampilan `cv2.imshow`, Anda disarankan menjalankannya langsung di lingkungan Python Windows karena file ini murni menggunakan socket dan OpenCV standar.

---

## 5. Sinkronisasi dengan Laptop GCS Lain
Jika Anda ingin menyalin modul ini ke laptop GCS satunya, Anda cukup menyalin folder [receiver/](file:///C:/Users/Ardi/OneDrive/Dokumen/Jarkom_lanjut/receiver) ini. Modul ini sudah sepenuhnya kompatibel dengan spesifikasi pengirim baseline Drone 1.
