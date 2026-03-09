import time
import threading
from collections import deque

class MockSerial:
    """
    Simula un puerto serial para el firmware ArduinoBoardFirmware.
    - write(): Imprime el comando y genera un ACK en la cola de lectura.
    - readline(): Devuelve ACKs de la cola o lecturas ultrasónicas periódicas.
    """
    def __init__(self, port="/dev/mock", baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_open = True
        self.is_mock = True
        
        self._read_queue = deque()
        self._lock = threading.Lock()
        
        # Hilo para generar lecturas ultrasónicas periódicas
        self._stop_us = threading.Event()
        self._us_thread = threading.Thread(target=self._generate_us, daemon=True)
        self._us_thread.start()

    def write(self, data: bytes):
        line = data.decode('ascii', errors='ignore').strip()
        print(f"[MOCK SERIAL →] {line}")
        
        # Generar ACK automático basado en el protocolo {BASE}:{ID}:{CMD}
        parts = line.split(':')
        if len(parts) >= 2:
            base_id = parts[0]
            spec_id = parts[1]
            
            ack = ""
            if base_id == "EYE":
                ack = f"{spec_id}:EYE:ok\n"
            elif base_id == "MOT":
                ack = f"{spec_id}:STATE:ok\n"
            elif base_id == "LED":
                ack = f"{spec_id}:STATE:ok\n"
            elif base_id == "LCD":
                ack = f"{spec_id}:TEXT:ok\n"
            elif base_id == "BUZZ":
                ack = f"{spec_id}:STATE:ok\n"
            elif base_id == "US" and parts[2] == "PING":
                ack = f"{spec_id}:15.5\n"
            
            if ack:
                with self._lock:
                    self._read_queue.append(ack.encode('ascii'))

    def readline(self) -> bytes:
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            with self._lock:
                if self._read_queue:
                    return self._read_queue.popleft()
            time.sleep(0.01)
        return b""

    def flush(self):
        pass

    def close(self):
        self.is_open = False
        self._stop_us.set()

    def _generate_us(self):
        """Genera lecturas US_1 cada 1 segundo si no hay nada en cola."""
        while not self._stop_us.is_set():
            time.sleep(1.0)
            with self._lock:
                # Solo añadir si la cola no está demasiado llena
                if len(self._read_queue) < 5:
                    self._read_queue.append(b"US_1:25.0\n")
                    self._read_queue.append(b"US_2:30.5\n")
