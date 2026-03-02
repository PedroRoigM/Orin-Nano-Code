import serial
import threading

from controllers.shared_port import SharedPort
from controllers.ultrasonic_observer import UltrasonicObserver
from controllers.tank_controller import TankController
from controllers.led_controller import LedController
from controllers.lcd_controller import LcdController


class ArduinoController:
    """
    Controlador central del Arduino.

    Abre UNA sola conexión serial y la comparte entre todos los
    sub-controladores y el observador ultrasónico.

    El hilo del observador sólo lee (readline); todos los demás
    escriben a través de SharedPort con un único write_lock, por lo que
    no hay colisiones.

    Uso:
        arduino = ArduinoController("/dev/ttyACM0")
        arduino.start()

        arduino.tank.forward(50)
        arduino.leds.set_color(255, 0, 0)
        arduino.lcd.display_text("Hola!", line=0)

        if arduino.ultrasonic.is_front_blocked:
            arduino.tank.stop()

        arduino.stop()   # al salir del programa
    """

    def __init__(
        self,
        port_name: str,
        baudrate: int = 9600,
        ultrasonic_threshold_cm: float = 10.0,
    ):
        # ── Shared serial ────────────────────────────────────────────
        self._ser        = serial.Serial(port_name, baudrate, timeout=1)
        self._write_lock = threading.Lock()
        self._port       = SharedPort(self._ser, self._write_lock)

        # ── Safety observer (reads only) ─────────────────────────────
        self.ultrasonic = UltrasonicObserver(
            self._ser,
            threshold_cm=ultrasonic_threshold_cm,
        )

        # ── Movement ─────────────────────────────────────────────────
        self.tank = TankController(self._port)

        # ── Output peripherals ───────────────────────────────────────
        self.leds = LedController(self._port)
        self.lcd  = LcdController(self._port)

        print(f"[Arduino] Connected on {port_name} @ {baudrate} baud")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Starts the ultrasonic observer background thread."""
        self.ultrasonic.start()
        print("[Arduino] Ultrasonic observer started")

    def stop(self) -> None:
        """Stops movement and the observer, then closes the serial port."""
        self.tank.stop()
        self.ultrasonic.stop()
        if self._ser.is_open:
            self._ser.close()
        print("[Arduino] Stopped and port closed")

    # ------------------------------------------------------------------
    # Convenience safety helpers
    # ------------------------------------------------------------------

    @property
    def can_move_forward(self) -> bool:
        return not self.ultrasonic.is_front_blocked

    @property
    def can_move_backward(self) -> bool:
        return not self.ultrasonic.is_back_blocked

    @property
    def can_turn(self) -> bool:
        return not self.ultrasonic.is_blocked