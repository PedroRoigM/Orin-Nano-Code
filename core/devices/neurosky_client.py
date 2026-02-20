# src/devices/neurosky_client.py
import socket
import json


class NeuroSkyClient:
    def __init__(self, host='127.0.0.1', port=13854):
        self.host = host
        self.port = port
        self.sock = None
        self._buffer = ""

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.sock.settimeout(2.0)
        config = {"enableRawOutput": True, "format": "Json"}
        self.sock.sendall(json.dumps(config).encode('utf-8'))
        print("Conectado a NeuroSky")

    def read_data(self) -> dict:
        """
        Lee del stream TCP acumulando en buffer hasta encontrar
        un JSON completo terminado en newline/carriage return.
        """
        try:
            while True:
                chunk = self.sock.recv(4096).decode('utf-8', errors='ignore')
                if not chunk:
                    break
                self._buffer += chunk

                # ThinkGear envía un JSON por línea, delimitado por \r
                while '\r' in self._buffer or '\n' in self._buffer:
                    for delim in ('\r\n', '\r', '\n'):
                        if delim in self._buffer:
                            line, self._buffer = self._buffer.split(delim, 1)
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                parsed = json.loads(line)
                                # Solo devolver frames con datos EEG completos
                                if "eegPower" in parsed or "eSense" in parsed or "poorSignalLevel" in parsed:
                                    return parsed
                            except json.JSONDecodeError:
                                pass  # línea incompleta, seguir acumulando
                            break

        except socket.timeout:
            pass
        except Exception as e:
            print(f"[ERROR] Desconocido al leer datos: {e}")
        return {}

    def close(self):
        if self.sock:
            self.sock.close()
            print("Conexión cerrada.")