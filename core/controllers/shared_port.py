"""
shared_port.py
==============
Wrapper serial thread-safe compartido entre todos los controladores
del nuevo firmware (ArduinoBoardFirmware).

Protocolos soportados:
  · Texto (nuevo):   send_line("MOT:FWD,150")   ← nuevo firmware
  · Binario (viejo): send_data([...])            ← backward compat

El puerto permanece abierto durante toda la vida de ArduinoController.
No lo cierra nunca: el propietario gestiona el ciclo de vida.
"""

import serial
import threading


class SharedPort:
    """
    Drop-in replacement para Port que usa un serial.Serial ya abierto,
    compartido entre múltiples controladores y el listener serial.

    send_line() y send_data() son thread-safe vía un único write_lock.
    """

    # Constantes protocolo binario (sin cambios)
    _BUFFER_START = 64   # '@'
    _BUFFER_END   = 13   # CR

    def __init__(self, ser: serial.Serial, write_lock: threading.Lock):
        self._ser  = ser
        self._lock = write_lock

    # ── Protocolo texto (nuevo firmware ArduinoBoardFirmware) ────────────────

    def send_line(self, line: str) -> None:
        """
        Envía "TIPO:PAYLOAD\n" al Arduino. Thread-safe.
        El '\n' se añade automáticamente si falta.
        Ejemplo: send_line("LED:BLINK") → envía b"LED:BLINK\n"
        """
        if not line.endswith('\n'):
            line += '\n'
        try:
            with self._lock:
                self._ser.write(line.encode('ascii'))
                self._ser.flush()
        except serial.SerialException as exc:
            print(f"[SharedPort] Write error: {exc}")

    # ── Protocolo binario (firmware antiguo — no modificar) ──────────────────

    def send_data(self, data: list[int]) -> None:
        """
        Envía frame binario [0x40, ...data, 0x0D]. Thread-safe.
        Mantiene compatibilidad con AudioController, ServoController, etc.
        """
        payload = bytes([self._BUFFER_START] + data + [self._BUFFER_END])
        try:
            with self._lock:
                self._ser.write(payload)
                self._ser.flush()
        except serial.SerialException as exc:
            print(f"[SharedPort] Write error (binary): {exc}")


if __name__ == "__main__":
    import serial as _serial
    # Abrir UNA SOLA vez — send_line cierra tras cada envío (DTR reset)
    # Para pruebas usar conexión persistente directamente:
    ser = _serial.Serial('/dev/cu.usbmodem2101', 9600, timeout=1)
    write_lock = threading.Lock()
    port = SharedPort(ser, write_lock)

    port.send_line("EYE:EYES_1:50,0,255,0,0\n")
