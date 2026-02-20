import socket
import json

class UDPSender:
    def __init__(self, ip='127.0.0.1', port=7000):
        self.address = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, data):
        try:
            json_data = json.dumps(data) + '\n'  # <--- CLAVE
            self.sock.sendto(json_data.encode('utf-8'), self.address)
        except Exception as e:
            print(f"[ERROR] UDP Send Failed: {e}")