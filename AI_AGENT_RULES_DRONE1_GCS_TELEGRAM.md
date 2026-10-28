# Aturan Main dan Tugas AI Agent — Proyek Drone 1, GCS, GPS, dan Telegram

> **Tujuan dokumen:** Menjadi instruksi kerja utama bagi AI Agent agar implementasi tetap sesuai ruang lingkup, urutan, protokol yang sudah ada, dan kondisi nyata proyek.
>
> **Bahasa kerja:** Bahasa Indonesia. Nama teknis, perintah terminal, nama file, protokol, dan kode boleh tetap dalam bahasa aslinya.

---

## 1. Misi Utama

Bangun sistem pemantauan **Drone 1** dengan kemampuan:

1. Mengirim video dari kamera bawaan HP Android yang dipasang pada Drone 1 ke GCS secara realtime.
2. Mengirim lokasi GPS HP Android secara berkala ke GCS.
3. Menampilkan video dan informasi GPS di GCS.
4. Mengintegrasikan Telegram Bot untuk status, lokasi, foto, dan notifikasi.
5. Mempertahankan jalur video UDP yang telah ada sampai perubahan terbukti diperlukan dan diuji.

AI Agent harus bekerja bertahap, menguji tiap bagian, dan tidak menganggap fitur berhasil hanya karena kode sudah ditulis.

## 2. Kondisi Proyek yang Sudah Diketahui

Gunakan bagian ini sebagai baseline. Jangan mengubah fakta ini tanpa bukti baru dari pengguna atau pengujian.

- Perangkat Drone 1 yang direncanakan: **HP Android**, menggunakan kamera dan GPS HP.
- HP dan laptop GCS direncanakan berada pada jaringan Wi-Fi/hotspot yang sama.
- GCS memakai Windows dengan Ubuntu 24.04 di WSL2.
- Receiver video Python di WSL pernah menerima paket UDP pada port `5002`.
- Log receiver pernah menunjukkan frame JPEG lengkap dan berhasil didekode pada resolusi `640x480`.
- Paket video yang masuk terlihat di WSL dengan tujuan `172.20.107.153:5002`; Windows PowerShell juga pernah melihat paket dari pengirim dan meneruskannya ke WSL.
- Tampilan GUI/OpenCV di WSL pernah bermasalah. Jangan menganggap masalah video yang terlihat pasti berasal dari sender; penerimaan dan decoding pernah berhasil.
- Port GPS `5003` adalah **rancangan baru yang diusulkan**, bukan fakta bahwa layanan GPS sudah berjalan.
- Telegram Bot belum dibuat pada saat dokumen ini ditulis.
- Kode sender lama, protokol chunk video lengkap, kode forwarding PowerShell, dan implementasi Android belum dikonfirmasi/ditinjau secara menyeluruh.

### Aturan tentang fakta dan asumsi

Selalu tandai informasi penting sebagai salah satu dari:
- **Terverifikasi:** terlihat dari kode, output, log, atau pengujian yang diberikan.
- **Rancangan:** keputusan yang disepakati tetapi belum diuji.
- **Asumsi:** dugaan sementara yang perlu dikonfirmasi.

Jangan mengubah asumsi menjadi fakta. Jangan mengarang nama file, IP, port, format paket, output perintah, atau hasil pengujian.

## 3. Arsitektur Target

Pisahkan jalur video dan GPS.

```text
HP Android di Drone 1
├── Kamera Android
│   └── Video sender Android
│       └── UDP video (port/protokol mengikuti receiver lama)
└── GPS Android
    └── GPS sender
        └── UDP GPS (port 5003 adalah rancangan awal, perlu konfirmasi)

Jaringan Wi-Fi / hotspot
        │
        ▼
GCS Windows / WSL2
├── Jalur video: pertahankan protokol UDP yang sudah ada
├── Jalur GPS: terima JSON, validasi, simpan posisi terbaru
├── Tampilan GCS: video + koordinat + waktu update + status koneksi
└── Telegram Bot
    ├── /start
    ├── /gps
    ├── /status
    ├── /photo (hanya setelah alur pengambilan/penyimpanan foto diterapkan)
    └── notifikasi yang disepakati
```

### Prinsip arsitektur

- **Video dan GPS adalah dua jalur data terpisah.** Jangan mencampur paket GPS dengan protokol chunk video.
- Telegram pada rancangan awal berjalan melalui GCS. Hindari menaruh token bot di aplikasi Android.
- IP Windows yang dapat dijangkau HP harus diperoleh dari adapter Wi-Fi/hotspot yang aktif. Jangan otomatis menggunakan IP internal WSL `172.20.x.x` sebagai alamat tujuan HP.
- Jangan menebak IP laptop. Minta pengguna menjalankan `ipconfig` dan mengidentifikasi adapter yang benar.
- UDP tidak menjamin paket sampai. Terapkan timeout, validasi, dan status data basi/disconnected pada GCS.
- GPS HP menunjukkan lokasi HP. Jangan menyebutnya posisi flight controller atau posisi drone yang sebenarnya kecuali HP memang terpasang pada drone dan asumsi itu diterima secara eksplisit.
- Pengiriman setiap satu detik adalah target awal, bukan jaminan GPS menghasilkan fix baru setiap detik.
- Telegram adalah kanal monitoring/notifikasi, bukan pengganti GCS atau sistem flight control.

## 4. Urutan Kerja Wajib

AI Agent harus mengikuti urutan ini. Jangan lompat ke tahap berikutnya sebelum tahap aktif lulus uji atau pengguna menyetujui penundaan.

### Tahap 0 — Audit dan baseline

1. Minta/temukan file proyek yang benar-benar tersedia.
2. Baca sender lama, `udp_video_receiver.py`, forwarding PowerShell, dan dependensi yang terkait.
3. Catat protokol video: port, struktur header, ukuran/chunk, ID frame, penanda akhir frame, encoding, timeout, dan aturan reassembly.
4. Catat cara menjalankan program saat ini dan hasil yang sudah terbukti.
5. Buat ringkasan baseline sebelum menyarankan perubahan.

**Exit criteria:** protokol video yang ada dipahami cukup untuk memastikan sender Android akan kompatibel. Jika sender atau protokol tidak tersedia, berhenti dan minta file/log yang diperlukan; jangan menebak protokol.

### Tahap 1 — GPS Android ke GCS

1. Konfirmasi IP laptop pada adapter Wi-Fi/hotspot yang digunakan.
2. Pastikan port GPS yang disepakati (default usulan `5003`) tidak berbenturan.
3. Buat receiver GPS sederhana dengan validasi JSON dan rentang koordinat.
4. Buat sender GPS Android menggunakan izin lokasi yang sesuai.
5. Uji paket aktual sampai terlihat di GCS.
6. Tampilkan waktu penerimaan dan usia data agar posisi basi terdeteksi.

**Exit criteria:** GCS menerima koordinat nyata dari HP dan dapat membedakan data baru dengan data basi.

### Tahap 2 — Integrasi Telegram dasar

1. Bantu pengguna membuat bot lewat BotFather.
2. Simpan token dalam environment variable atau file konfigurasi lokal yang tidak masuk version control.
3. Batasi akses bot berdasarkan `chat_id` yang diizinkan.
4. Implementasikan `/start`, `/gps`, dan `/status`.
5. Uji saat GPS tersedia, tidak tersedia, dan basi.

**Exit criteria:** bot hanya melayani pengguna yang diizinkan dan mengembalikan status yang sesuai data aktual.

### Tahap 3 — Video dari kamera HP Android

1. Gunakan Android CameraX atau implementasi Android yang sesuai.
2. Jangan langsung mengganti receiver GCS.
3. Cocokkan implementasi sender Android dengan protokol sender lama dan receiver yang telah diaudit.
4. Jika protokol lama tidak praktis untuk Android, jelaskan opsi migrasi dan dampaknya; minta persetujuan sebelum mengubah protokol.
5. Mulai dari resolusi/frame rate rendah untuk pengujian.
6. Validasi bahwa frame diterima, dirakit, didekode, dan ditampilkan.

**Exit criteria:** video dari kamera HP tampil di GCS secara stabil tanpa merusak jalur yang sudah ada.

### Tahap 4 — Integrasi tampilan dan Telegram foto/notifikasi

1. Gabungkan video, GPS, waktu update, dan status koneksi pada GCS.
2. Terapkan `/photo` hanya jika ada implementasi jelas untuk mengambil/menyimpan foto terbaru.
3. Tambahkan notifikasi yang disepakati (misalnya GPS basi atau koneksi terputus) dengan cooldown agar tidak spam.
4. Jangan menambahkan geofence, pelacakan, kontrol penerbangan, atau fitur lain tanpa persetujuan pengguna.

**Exit criteria:** seluruh fitur yang disepakati dapat diuji bersama, dan status kegagalan terlihat jelas.

### Tahap 5 — Uji sistem menyeluruh

Uji setidaknya:
- HP dan GCS berada pada jaringan yang sama.
- GPS diizinkan dan memperoleh fix.
- GPS dimatikan/izin dicabut.
- HP kehilangan jaringan.
- Receiver video dihentikan.
- Telegram token salah atau bot tidak dapat terhubung.
- Program di-restart.
- Data GPS basi tidak dilaporkan sebagai realtime.

Catat hasil lulus/gagal, log relevan, dan langkah reproduksi.

## 5. Kontrak Data GPS

Format awal yang diusulkan:

```json
{
  "device": "drone1",
  "lat": -6.2001,
  "lon": 106.8167,
  "accuracy_m": 8.0,
  "timestamp": "2026-10-22T10:00:00Z"
}
```

Nilai koordinat di atas hanya contoh format, bukan koordinat sebenarnya.

Validasi minimum:
- `lat` angka pada rentang `-90..90`.
- `lon` angka pada rentang `-180..180`.
- `accuracy_m` boleh tidak tersedia; jika ada harus angka non-negatif.
- `timestamp` harus diparse dan zona waktunya ditangani dengan benar.
- Catat waktu penerimaan lokal GCS secara terpisah dari waktu pengukuran GPS.
- Data yang lebih tua dari ambang yang disepakati (awal usulan: 5 detik) harus ditandai basi, bukan ditampilkan sebagai realtime.
- Jangan menampilkan lokasi contoh atau koordinat default sebagai GPS nyata.

## 6. Kontrak Video

Sebelum menulis sender Android, dokumentasikan dari kode yang nyata:
- alamat/port tujuan dan interface jaringan;
- struktur header paket;
- ukuran maksimum payload;
- nomor urut paket/chunk;
- ID frame;
- cara mengetahui akhir frame;
- format frame (misalnya JPEG) dan metadata ukuran;
- timeout reassembly;
- perilaku ketika chunk hilang atau urutan berubah.

Jangan menganggap semua receiver menerima JPEG mentah. Jangan membuat header baru tanpa memeriksa kode receiver yang ada. Jika kode menggunakan protokol custom, implementasikan protokol itu secara eksplisit dan uji dengan paket nyata.

## 7. Aturan Telegram dan Keamanan

- Jangan meminta pengguna menempel token bot ke chat.
- Jangan menulis token, password, private key, atau kredensial ke log, source code publik, atau repository.
- Gunakan environment variable atau konfigurasi lokal yang diabaikan Git.
- Batasi command berdasarkan `chat_id` yang diizinkan.
- Validasi input dan tangani data GPS yang belum tersedia.
- `/gps` harus menyatakan kapan data terakhir diterima dan apakah masih segar.
- `/photo` tidak boleh mengklaim berhasil sebelum foto benar-benar tersedia dan pengiriman sukses.
- Hindari notifikasi berulang tanpa batas; terapkan cooldown.
- Jangan menambahkan perintah kontrol penerbangan atau perintah berisiko ke bot tanpa permintaan dan rancangan keselamatan yang eksplisit.

## 8. Aturan Modifikasi Kode

Sebelum mengubah kode:
1. Jelaskan file mana yang akan diubah dan mengapa.
2. Sebutkan risiko kompatibilitas.
3. Pertahankan versi kerja yang ada atau minta pengguna membuat backup/commit.
4. Buat perubahan sekecil mungkin.
5. Jangan mengganti banyak komponen sekaligus.
6. Jangan menghapus fitur atau mengubah port/protokol tanpa persetujuan.
7. Jangan menyatakan pengujian berhasil jika hanya melakukan inspeksi kode.
8. Jika tidak dapat menjalankan pengujian pada perangkat nyata, tandai sebagai **belum diuji pada perangkat nyata**.

Setelah perubahan:
1. Berikan perintah menjalankan program secara tepat.
2. Berikan output yang diharapkan, diberi label **contoh**, bukan output aktual.
3. Minta pengguna menjalankan tes dan mengirim output aktual bila akses perangkat tidak tersedia.
4. Berikan cara menghentikan program dan cara kembali ke versi sebelumnya bila perlu.

## 9. Aturan Komunikasi AI Agent

- Gunakan Bahasa Indonesia yang jelas dan langsung.
- Kerjakan satu tahap per satu waktu; jangan membanjiri pengguna dengan banyak tahap implementasi sekaligus.
- Berikan satu tindakan berikutnya yang paling penting.
- Saat meminta informasi, minta hanya informasi yang diperlukan untuk tahap aktif.
- Gunakan nama file dan alamat IP hanya jika sudah diverifikasi atau jelas diberi placeholder.
- Bedakan instruksi PowerShell Windows, shell Ubuntu/WSL, dan Termux Android dengan heading yang eksplisit.
- Jangan menyuruh menjalankan perintah Linux di PowerShell atau sebaliknya tanpa menjelaskan shell yang benar.
- Jangan mengklaim bisa mengakses perangkat pengguna secara langsung.
- Jangan menyimpulkan keberhasilan dari asumsi atau dari kode yang belum dijalankan.
- Jika ada konflik antara rencana baru dan protokol lama, prioritaskan menjaga fungsi yang sudah terverifikasi, jelaskan konflik, lalu minta keputusan pengguna.

## 10. Definisi Selesai (Definition of Done)

Proyek dianggap selesai hanya jika:
- [ ] Kamera HP Android mengirim video ke GCS secara realtime.
- [ ] Video kompatibel dengan receiver yang disepakati dan stabil dalam pengujian.
- [ ] GPS HP Android diterima GCS dan diperbarui secara berkala.
- [ ] GCS menunjukkan koordinat, waktu update, akurasi bila tersedia, dan status data basi.
- [ ] Telegram `/gps` dan `/status` berfungsi dengan pembatasan akses.
- [ ] `/photo` berfungsi jika fitur foto telah disetujui dan diterapkan.
- [ ] Notifikasi yang disepakati tidak spam dan menunjukkan kondisi aktual.
- [ ] Perilaku saat jaringan/izin GPS/receiver terputus sudah diuji.
- [ ] Instruksi setup, konfigurasi, menjalankan, menghentikan, dan troubleshooting terdokumentasi.
- [ ] Tidak ada token atau kredensial rahasia yang tertanam di source code/repository.
- [ ] Hasil tes nyata dibedakan dari hasil yang hanya diharapkan.

## 11. Format Laporan Tiap Sesi

AI Agent harus mengakhiri setiap sesi kerja dengan format ringkas berikut:

```text
TAHAP AKTIF:
TUJUAN:
FAKTA TERVERIFIKASI:
ASUMSI / YANG BELUM DIKETAHUI:
FILE YANG DIUBAH:
PERINTAH YANG DIJALANKAN:
HASIL TES AKTUAL:
STATUS: LULUS / GAGAL / TERBLOKIR / BELUM DIUJI
LANGKAH BERIKUTNYA (SATU SAJA):
```

Jangan menandai tahap sebagai LULUS tanpa bukti hasil tes.

## 12. Instruksi Awal untuk AI Agent

Mulai dengan **Tahap 0 — Audit dan baseline**. Jangan langsung membuat ulang seluruh sistem.

Pertama, minta atau cari file yang tersedia untuk:
1. sender video lama;
2. `udp_video_receiver.py`;
3. script PowerShell forwarding UDP;
4. perintah/log terakhir yang menunjukkan frame JPEG berhasil didekode.

Setelah membaca file, jelaskan protokol video yang benar-benar digunakan dan ajukan rencana perubahan minimum. Jika file tidak tersedia, minta pengguna mengunggahnya. Jangan menebak bagian yang belum diketahui.
