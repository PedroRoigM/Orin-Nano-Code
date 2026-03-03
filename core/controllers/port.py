"""
port.py
=======
Comunicación serial con Arduino. Soporta dos protocolos:

  Texto (nuevo firmware — ArduinoBoardFirmware):
        send_line("LED:ON")       →  "LED:ON\n"
        send_line("MOT:FWD,120")  →  "MOT:FWD,120\n"

  Binario (firmware antiguo — audio, servo, holo, teece…):
        send_data([76, 9, 4, 0, 255, 0, 0])
        →  [0x40, 76, 9, 4, 0, 255, 0, 0, 0x0D]

Cada llamada abre el puerto, escribe y cierra.
Para conexiones persistentes y multi-hilo usar SharedPort.
"""

import serial
import serial.tools.list_ports
from time import sleep


class Port:
    def __init__(self, port_name: str = '/dev/ttyACM0', baudrate: int = 9600):
        self.port_name = port_name.strip()
        self.connection = serial.Serial()
        self.connection.port     = self.port_name
        self.connection.baudrate = baudrate
        self.connection.bytesize = serial.EIGHTBITS
        self.connection.stopbits = serial.STOPBITS_ONE
        self.connection.parity   = serial.PARITY_NONE
        self.connection.timeout  = 1

    # ── Protocolo texto (nuevo firmware ArduinoBoardFirmware) ────────────────

    def send_line(self, line: str) -> None:
        """
        Envía un comando de texto al Arduino.
        Formato: "TIPO:PAYLOAD"  (el '\n' se añade automáticamente si falta).
        Ejemplo: send_line("LED:ON") → envía b"LED:ON\n"
        """
        if not line.endswith('\n'):
            line += '\n'
        try:
            if not self.connection.is_open:
                self.connection.open()
            self.connection.write(line.encode('ascii'))
            self.connection.flush()
        except Exception as e:
            print(f"[Port] ERROR send_line: {e}")
            raise
        finally:
            if self.connection.is_open:
                self.connection.close()

    # ── Protocolo binario (firmware antiguo — no modificar) ──────────────────

    def send_data(self, data: list[int]) -> list[int]:
        """
        Envía un array de bytes enmarcados (protocolo binario antiguo).
        Usado por AudioController, ServoController, HoloController, etc.
        Frame: [0x40, ...data, 0x0D]
        """
        _START = 64   # '@'
        _END   = 13   # CR
        payload = bytes([_START] + data + [_END])
        try:
            if not self.connection.is_open:
                self.connection.open()
            self.connection.write(payload)
            self.connection.flush()
            return list(payload)
        except Exception as e:
            print(f"[Port] ERROR send_data: {e}")
            raise
        finally:
            if self.connection.is_open:
                self.connection.close()

    @staticmethod
    def list_serial_ports():
        return serial.tools.list_ports.comports()


# ── Ejemplo de uso ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    p = Port('/dev/ttyACM0')
    p.send_line("LED:ON")
    sleep(1.0)
    p.send_line("LED:OFF")
    sleep(0.5)
    p.send_line("LCD:Hola R2!")
    sleep(0.5)
    p.send_line("BUZZ:1000,200")
