#!/usr/bin/env python3
"""
Photo Collector Tool (Pengumpul Foto Dataset Wajah Otomatis)
===========================================================
Gunakan tool ini jika ingin mengambil foto wajah lewat kamera laptop/webcam:
1. Masukkan nama orang (misal: Ardi).
2. Tekan tombol SPASI di jendela kamera untuk mengambil foto (target 15-20 foto),
   atau tekan 'a' untuk mode burst otomatis (mengambil 20 foto berturut-turut).
3. Tekan 'q' setelah selesai.
"""

import os
import time
import cv2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

def main():
    print("==================================================")
    print("        TOOL PENGUMPUL FOTO DATASET WAJAH         ")
    print("==================================================")
    person_name = input("Masukkan Nama Anggota (contoh: Ardi): ").strip()

    if not person_name:
        print("[!] Nama tidak boleh kosong!")
        return

    # Bersihkan nama agar aman untuk nama folder
    safe_name = "".join(c for c in person_name if c.isalnum() or c in ("_", "-")).strip()
    target_dir = os.path.join(DATASET_DIR, safe_name)
    os.makedirs(target_dir, exist_ok=True)

    print(f"\n[*] Folder penyimpanan: {target_dir}")
    print("[*] Membuka kamera laptop...")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[!] Gagal membuka webcam laptop.")
        return

    cascade_path = os.path.join(BASE_DIR, "models", "haarcascade_frontalface_default.xml")
    face_cascade = cv2.CascadeClassifier(cascade_path)

    photo_count = len([f for f in os.listdir(target_dir) if f.endswith(".jpg")])
    print(f"[*] Sudah ada {photo_count} foto di dalam folder ini.")
    print("\n[PETUNJUK KONTROL]")
    print(" - Tekan [SPASI] : Ambil 1 foto")
    print(" - Tekan [A]     : Auto-Burst (mengambil 20 foto otomatis)")
    print(" - Tekan [Q]     : Selesai / Keluar\n")

    auto_burst = False
    burst_remaining = 0
    last_burst_time = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        display_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(60, 60))

        # Tampilkan kotak bantu deteksi wajah
        for (x, y, w, h) in faces:
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Informasi di layar
        status_face_text = f"Wajah: OK ({len(faces)})" if len(faces) > 0 else "Wajah: BELUM TERDETEKSI"
        status_color = (0, 255, 0) if len(faces) > 0 else (0, 0, 255)
        cv2.putText(
            display_frame,
            f"Nama: {safe_name} | Foto: {photo_count} | {status_face_text}",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            status_color,
            2
        )
        if auto_burst:
            cv2.putText(
                display_frame,
                f"AUTO-BURST SISA: {burst_remaining}",
                (15, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 0, 255),
                2
            )

        cv2.imshow("Kamera Pengumpul Dataset", display_frame)
        key = cv2.waitKey(1) & 0xFF

        now = time.time()

        # Ambil foto jika tombol SPASI ditekan atau mode auto-burst
        should_save = False
        if key == 32:  # SPASI
            should_save = True
        elif key == ord('a') or key == ord('A'):
            auto_burst = True
            burst_remaining = 20
        elif key == ord('q') or key == ord('Q'):
            break

        if auto_burst and burst_remaining > 0 and (now - last_burst_time) >= 0.35:
            should_save = True
            burst_remaining -= 1
            last_burst_time = now
            if burst_remaining <= 0:
                auto_burst = False

        if should_save:
            if len(faces) > 0:
                photo_count += 1
                filename = os.path.join(target_dir, f"face_{int(now * 1000)}.jpg")
                cv2.imwrite(filename, frame)
                print(f"[+] Foto ke-{photo_count} tersimpan: {os.path.basename(filename)}")
            else:
                print("[-] Peringatan: Wajah tidak terdeteksi, foto dilewati agar dataset tidak rusak.")

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n[*] Selesai. Total {photo_count} foto tersimpan di: {target_dir}")
    print("[*] Jalankan 'python train_faces.py' untuk melatih model.")

if __name__ == "__main__":
    main()
