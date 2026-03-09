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
from concurrent.futures import Future
from collections import deque
from typing import Dict


class SharedPort:
    """
    Drop-in replacement para Port que usa un serial.Serial ya abierto,
    compartido entre múltiples controladores y el listener serial.

    send_line() y send_data() son thread-safe vía un único write_lock.
    Now follows a promise-based pattern for send_line.
    """

    # Constantes protocolo binario (sin cambios)
    _BUFFER_START = 64   # '@'
    _BUFFER_END   = 13   # CR

    def __init__(self, ser: serial.Serial, write_lock: threading.Lock):
        self._ser  = ser
        self._lock = write_lock
        
        # Registry of pending futures: { "LED_1": deque([f1, f2]), "MOT_1": ... }
        self._pending_responses: Dict[str, deque[Future]] = {}
        self._registry_lock = threading.Lock()

    # ── Protocolo texto (nuevo firmware ArduinoBoardFirmware) ────────────────

    def send_line(self, line: str) -> Future:
        """
        Envía "TIPO:ID:PAYLOAD\n" al Arduino. Thread-safe.
        Retorna un Future que se resolverá cuando el Arduino envíe el ACK.
        """
        if not line.endswith('\n'):
            line += '\n'
            
        future = Future()
        
        # Identify specific ID for tracking: e.g. "LED:LED_1:ON" -> "LED_1"
        parts = line.strip().split(':')
        if len(parts) >= 2:
            specific_id = parts[1]
            with self._registry_lock:
                if specific_id not in self._pending_responses:
                    self._pending_responses[specific_id] = deque()
                self._pending_responses[specific_id].append(future)
        else:
            # If malformed or doesn't follow BASE:ID:CMD, resolve with error immediately
            future.set_exception(ValueError(f"Malformed command: {line.strip()}"))
            return future

        try:
            with self._lock:
                self._ser.write(line.encode('ascii'))
                self._ser.flush()
        except Exception as exc:
            print(f"[SharedPort] Write error: {exc}")
            future.set_exception(exc)
            # Cleanup from registry if write failed
            with self._registry_lock:
                if specific_id in self._pending_responses and future in self._pending_responses[specific_id]:
                    self._pending_responses[specific_id].remove(future)
                    
        return future

    def resolve_response(self, specific_id: str, payload: str) -> None:
        """
        Llamado por el UltrasonicObserver cuando llega una línea del serial.
        Resuelve el Future más antiguo para el specific_id dado.
        """
        with self._registry_lock:
            if specific_id in self._pending_responses and self._pending_responses[specific_id]:
                future = self._pending_responses[specific_id].popleft()
                if not future.done():
                    future.set_result(payload)

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
