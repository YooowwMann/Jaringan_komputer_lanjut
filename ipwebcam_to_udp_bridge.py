#!/usr/bin/env python3
"""
IP Webcam to UDP Bridge (Drone 1 Streamer) - Low Latency Edition
================================================================
Membaca stream video dari aplikasi Android "IP Webcam" via HTTP
dengan threading pembaca frame tercepat (Zero-Buffer / Realtime),
lalu memotong dan membungkusnya menjadi paket UDP socket port 5002
dengan header biner '!IHH' (8 bytes).
"""

import sys
import time
import socket
import struct
import threading
import cv2

# ============================================================
# KONFIGURASI PENGIRIMAN UDP KE GCS RECEIVER
# ============================================================
GCS_UDP_IP = "127.0.0.1"        # Localhost (karena receiver ada di laptop yang sama)
GCS_UDP_PORT = 5002            # Port receiver video UDP
CHUNK_SIZE = 1100              # Maksimal byte payload per paket UDP (di bawah MTU 1500)
HEADER_STRUCT = "!IHH"         # frame_id (uint32), chunk_id (uint16), total_chunks (uint16)
HEADER_SIZE = struct.calcsize(HEADER_STRUCT)  # 8 bytes

# Pengaturan resolusi & kualitas video (dioptimasi untuk low-latency)
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
JPEG_QUALITY = 45

class FreshFrameReader:
    """
    Reader terpisah di thread latar belakang untuk membuang antrean buffer HTTP OpenCV.
    Hanya menyimpan 1 frame terbaru secara instan (Zero Latency).
    """
    def __init__(self, src):
        self.src = src
        self.cap = cv2.VideoCapture(self.src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.ret = False
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()

    def _reader_loop(self):
        while self.running:
            if not self.cap.isOpened():
                time.sleep(0.5)
                continue
            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self.lock:
                    self.ret = ret
                    self.frame = frame
            else:
                time.sleep(0.01)

    def read(self):
        with self.lock:
            if self.frame is not None:
                return self.ret, self.frame.copy()
            return False, None

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self.running = False
        if self.cap.isOpened():
            self.cap.release()

def run_bridge(phone_video_url):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("==================================================")
    print("  IP WEBCAM -> UDP BRIDGE (ZERO BUFFER REALTIME)  ")
    print("==================================================")
    print(f"[*] Menghubungkan ke HP : {phone_video_url}")
    print(f"[*] Target Kirim UDP    : {GCS_UDP_IP}:{GCS_UDP_PORT}")
    print(f"[*] Header Format       : '{HEADER_STRUCT}' ({HEADER_SIZE} bytes)")
    print(f"[*] Chunk Size          : {CHUNK_SIZE} bytes/paket")
    print(f"[*] Target Resolusi     : {FRAME_WIDTH}x{FRAME_HEIGHT} @ Q{JPEG_QUALITY}")
    print("[*] Tekan CTRL+C untuk menghentikan bridge.\n")

    frame_id = 0
    reader = None

    try:
        while True:
            if reader is None or not reader.isOpened():
                print(f"[*] Membuka stream kamera HP ({phone_video_url})...")
                reader = FreshFrameReader(phone_video_url)
                # Tunggu frame pertama
                for _ in range(30):
                    ret, test_frame = reader.read()
                    if ret and test_frame is not None:
                        break
                    time.sleep(0.1)

                if not reader.ret:
                    print("[!] Belum menerima frame dari HP. Coba lagi dalam 2 detik...")
                    reader.release()
                    reader = None
                    time.sleep(2)
                    continue
                print("[+] Stream kamera HP aktif & buffer dibuang (Realtime mode ON)!")

            ret, frame = reader.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            # Resize ke 640x480 agar ringan dan instan di jaringan
            if frame.shape[1] != FRAME_WIDTH or frame.shape[0] != FRAME_HEIGHT:
                frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))

            # Encode frame ke format JPEG
            success, encoded_jpeg = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
            )

            if not success:
                continue

            jpeg_bytes = encoded_jpeg.tobytes()
            total_bytes = len(jpeg_bytes)
            total_chunks = (total_bytes + CHUNK_SIZE - 1) // CHUNK_SIZE

            # Kirim per chunk via UDP
            for chunk_id in range(total_chunks):
                offset = chunk_id * CHUNK_SIZE
                chunk_data = jpeg_bytes[offset : offset + CHUNK_SIZE]

                header = struct.pack(HEADER_STRUCT, frame_id, chunk_id, total_chunks)
                packet = header + chunk_data

                sock.sendto(packet, (GCS_UDP_IP, GCS_UDP_PORT))

            frame_id = (frame_id + 1) % 4294967296  # Wrap uint32

            print(
                f"\r[REALTIME] Frame: {frame_id} | Ukuran: {total_bytes / 1024:.1f} KB | "
                f"Chunks: {total_chunks} paket UDP -> {GCS_UDP_PORT}",
                end="",
                flush=True
            )

            # Limit transmisi agar tidak membebani socket lokal (~30 FPS)
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\n\n[*] Bridge dihentikan oleh pengguna.")
    finally:
        if reader is not None:
            reader.release()
        sock.close()
        print("[*] Socket ditutup. Selesai.")

if __name__ == "__main__":
    default_url = "http://10.90.32.215:8080/video"

    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        print(f"Masukkan URL stream IP Webcam dari layar HP Anda.")
        print(f"Tekan ENTER langsung untuk menggunakan default ({default_url})")
        user_input = input("URL HP: ").strip()
        target_url = user_input if user_input else default_url

    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = "http://" + target_url

    if not target_url.endswith("/video"):
        if not target_url.endswith("/"):
            target_url += "/video"
        else:
            target_url += "video"

    run_bridge(target_url)
