#!/usr/bin/env python3
"""
Face Recognition Trainer (LBPH Model)
=====================================
Melatih model pengenalan wajah untuk 2 orang (atau lebih) dari folder dataset/.
Model yang dihasilkan akan otomatis digunakan oleh GCS Video Receiver untuk
mendeteksi wajah, memunculkan kotak nama, dan menandai orang asing sebagai UNKNOWN.
"""

import os
import json
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_FILE = os.path.join(MODELS_DIR, "face_recognizer.xml")
LABELS_FILE = os.path.join(MODELS_DIR, "labels.json")

os.makedirs(MODELS_DIR, exist_ok=True)

def train_model():
    print("==================================================")
    print("      FACE RECOGNITION TRAINER (DRONE 1)          ")
    print("==================================================")

    cascade_path = os.path.join(MODELS_DIR, "haarcascade_frontalface_default.xml")
    if not os.path.exists(cascade_path):
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    subdirs = [
        d for d in os.listdir(DATASET_DIR)
        if os.path.isdir(os.path.join(DATASET_DIR, d)) and not d.startswith(".")
    ]

    if not subdirs:
        print(f"[!] Error: Tidak ada folder orang di dalam {DATASET_DIR}")
        print("    Buat folder untuk setiap orang (contoh: dataset/Ardi dan dataset/Budi)")
        return

    print(f"[*] Ditemukan {len(subdirs)} target identitas: {subdirs}\n")

    faces_data = []
    labels_data = []
    labels_map = {}  # {label_id: person_name}

    total_images_processed = 0

    for label_id, person_name in enumerate(sorted(subdirs)):
        labels_map[label_id] = person_name
        person_dir = os.path.join(DATASET_DIR, person_name)
        image_files = [
            f for f in os.listdir(person_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        print(f"[*] Memproses '{person_name}': {len(image_files)} gambar ditemukan...")
        faces_for_person = 0

        for img_name in image_files:
            img_path = os.path.join(person_dir, img_name)
            img = cv2.imread(img_path)
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            detected = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=3,
                minSize=(40, 40)
            )

            # Jika wajah terdeteksi, ambil crop wajah
            if len(detected) > 0:
                # Ambil wajah terbesar jika ada lebih dari 1
                detected = sorted(detected, key=lambda b: b[2] * b[3], reverse=True)
                (x, y, w, h) = detected[0]
                face_crop = gray[y : y + h, x : x + w]
                face_resized = cv2.resize(face_crop, (200, 200))
                # Normalisasi pencahayaan dengan Equalize Histogram agar tahan variasi cahaya
                face_equalized = cv2.equalizeHist(face_resized)
                faces_data.append(face_equalized)
                labels_data.append(label_id)

                # Augmentasi horizontal flip (mirroring) agar model tahan sudut pandang kiri & kanan
                face_flipped = cv2.flip(face_equalized, 1)
                faces_data.append(face_flipped)
                labels_data.append(label_id)

                faces_for_person += 2
                total_images_processed += 2
            else:
                # PENTING: Jangan gunakan foto satu ruangan penuh karena akan mencemari LBPH!
                # Lewati foto yang gagal dideteksi agar model tetap akurat
                pass

        print(f"    -> Berhasil mengekstrak {faces_for_person} sampel wajah valid untuk '{person_name}'.")

    if not faces_data:
        print("\n[!] Gagal: Tidak ada sampel wajah valid yang dapat diekstrak.")
        return

    print("\n[*] Melatih model LBPH Face Recognizer...")
    recognizer = cv2.face.LBPHFaceRecognizer_create(
        radius=1,
        neighbors=8,
        grid_x=8,
        grid_y=8
    )
    recognizer.train(faces_data, np.array(labels_data))

    # Simpan model XML
    recognizer.save(MODEL_FILE)
    print(f"[+] Model berhasil disimpan ke: {MODEL_FILE}")

    # Simpan mapping label JSON
    with open(LABELS_FILE, "w") as f:
        json.dump(labels_map, f, indent=2)
    print(f"[+] Mapping label disimpan ke: {LABELS_FILE}")

    print("\n" + "=" * 50)
    print("        PELATIHAN MODEL SELESAI & SUKSES!        ")
    print("=" * 50)
    print(f"Total wajah yang dipelajari : {total_images_processed}")
    print(f"Daftar Orang Dikenali       : {labels_map}")
    print("Orang di luar daftar di atas akan otomatis berlabel [UNKNOWN].\n")

if __name__ == "__main__":
    train_model()
