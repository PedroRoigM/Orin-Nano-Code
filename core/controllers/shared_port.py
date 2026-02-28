import serial
import threading


class SharedPort:
    """
    Drop-in replacement for Port that uses an already-open serial.Serial
    shared across multiple controllers and the UltrasonicObserver.

    send_data() is thread-safe via a write lock.
    The serial is never closed here — the owner (ArduinoController) manages its lifecycle.
    """

    BUFFER_START = 64   # '@'
    BUFFER_END   = 13   # CR

    def __init__(self, ser: serial.Serial, write_lock: threading.Lock):
        self._ser  = ser
        self._lock = write_lock

    def send_data(self, data: list[int]) -> None:
        payload = bytes([self.BUFFER_START] + data + [self.BUFFER_END])
        try:
            with self._lock:
                self._ser.write(payload)
                self._ser.flush()
        except serial.SerialException as exc:
            print(f"[SharedPort] Write error: {exc}")
