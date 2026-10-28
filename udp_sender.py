import socket
import time

GCS_IP = "192.168.137.1"
PORT = 5002

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for i in range(10):
    message = f"Halo dari Drone 2 - paket {i+1}"
    sock.sendto(message.encode(), (GCS_IP, PORT))
    print(f"Terkirim: {message}")
    time.sleep(1)

sock.close()
print("Selesai.")
