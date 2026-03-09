"""
arduino_controller.py
=====================
Controlador central del Arduino (nuevo firmware ArduinoBoardFirmware).

Abre UNA sola conexión serial y la comparte entre todos los sub-controladores.
El UltrasonicObserver actúa como listener general bidireccional:
  · Lee TODAS las líneas del Arduino (US, LED_ack, LCD_ack, MOT_ack, BUZZ_ack).
  · Mantiene el estado de seguridad (distancia/bloqueo).
  · Todos los demás sub-controladores solo ESCRIBEN vía SharedPort con write_lock.

Uso básico:
    arduino = ArduinoController("/dev/ttyACM0")
    arduino.start()

    arduino.tank.forward(100)
    arduino.leds.on()
    arduino.lcd.display_text("Hola R2!")
    arduino.buzzer.beep()

    if arduino.can_move_forward:
        arduino.tank.forward(100)
    else:
        arduino.tank.stop()
        arduino.buzzer.react_to_obstacle(arduino.ultrasonic.distance_cm)

    arduino.stop()

Reacción automática al ultrasónico:
    ArduinoController puede configurarse con callbacks para reaccionar
    automáticamente cuando el sensor detecta un obstáculo:
        arduino.on_obstacle = lambda cm: arduino.tank.stop()
"""

import serial
import threading
import time
from typing import Optional, Callable

from controllers.shared_port          import SharedPort
from controllers.ultrasonic_observer  import UltrasonicObserver
from controllers.tank_controller      import TankController
from controllers.led_controller       import LedController
from controllers.lcd_controller       import LcdController
from controllers.buzzer_controller    import BuzzerController
from controllers.eyes_controller      import EyesController
from controllers.emotion_manager      import EmotionManager


class ArduinoController:
    """
    Controlador central para el nuevo firmware ArduinoBoardFirmware.

    Sub-controladores expuestos:
      .tank        — TankController    (MOT:FWD/REV/STOP)
      .leds        — LedController     (LED:ON/OFF/BLINK)
      .lcd         — LcdController     (LCD:<texto>)
      .buzzer      — BuzzerController  (BUZZ:<freq>,<ms> / BUZZ:OFF)
      .eyes        — EyesController    (EYES:<emo>,r,g,b,sq,wd / GAZE:gx,gy)
      .ultrasonic  — UltrasonicObserver (listener serial + estado US)

    Propiedades de seguridad (compatibles con tensor_rt.py):
      .can_move_forward   → True si el sensor no detecta obstáculo
      .can_move_backward  → True (sin sensor trasero en el nuevo firmware)
      .can_turn           → True si el sensor no detecta obstáculo

    Callback de obstáculo:
      .on_obstacle = lambda distance_cm: ...
      Se llama automáticamente cuando el sensor pasa de libre a bloqueado.
    """

    def __init__(
        self,
        port_name:               str,
        baudrate:                int   = 9600,
        ultrasonic_threshold_cm: float = 10.0,
        verbose:                 bool  = False,
    ):
        # ── Puerto serial compartido ──────────────────────────────────────────
        self._ser        = serial.Serial(port_name, baudrate, timeout=1)
        print(f"[Arduino] Puerto abierto — esperando reset del Arduino (2 s)…")
        time.sleep(2.0)   # el DTR activa el reset del Arduino; esperar a que arranque
        self._write_lock = threading.Lock()
        self._port       = SharedPort(self._ser, self._write_lock)

        # ── Listener / observer ultrasónico (lector único del serial) ─────────
        self.ultrasonic = UltrasonicObserver(
            ser           = self._ser,
            threshold_cm  = ultrasonic_threshold_cm,
            write_port    = self._port,
            controller_id = "US_1",
            verbose_acks  = verbose,
            verbose_us    = True,
        )

        # ── Controladores de actuadores ───────────────────────────────────────
        self.tank   = TankController(self._port,   controller_id="MOT_1",  verbose=verbose)
        self.leds   = LedController(self._port,    controller_id="LED_1",  verbose=verbose)
        self.lcd    = LcdController(self._port,    controller_id="LCD_1",  verbose=verbose)
        self.buzzer = BuzzerController(self._port,  controller_id="BUZZ_1", verbose=verbose)
        self.eyes   = EyesController(self._port,   controller_id="EYE_1",  verbose=verbose)

        # ── Gestor de emociones y comportamiento (desacoplado) ────────────────
        self.emotions = EmotionManager(self)

        # ── Callback de obstáculo (opcional) ──────────────────────────────────
        # Asignar una función para reacción automática al sensor:
        #   arduino.on_obstacle = lambda cm: (arduino.tank.stop(), arduino.buzzer.beep(800, 100))
        self.on_obstacle: Optional[Callable[[float], None]] = None

        # Conectar el callback interno al observer
        self.ultrasonic.on_ack["US"] = None   # reservado para futuros ACKs
        self._register_obstacle_watcher()

        print(f"[Arduino] Conectado en {port_name} @ {baudrate} baud | "
              f"umbral US: {ultrasonic_threshold_cm} cm")

    def test_all_interfaces(self) -> None:
        """Prueba la comunicación con todos los actuadores."""
        print("\n--- INICIANDO PRUEBAS DE INTERFAZ ARDUINO ---")
        self.ultrasonic.test_interface()
        self.tank.test_interface()
        self.leds.test_interface()
        self.lcd.test_interface()
        self.buzzer.test_interface()
        self.eyes.test_interface()
        print("--- PRUEBAS FINALIZADAS ---\n")

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """Arranca el listener serial en background."""
        self.ultrasonic.start()
        print("[Arduino] Listener serial arrancado.")

    def stop(self) -> None:
        """Para el motor, detiene el listener y cierra el puerto serial."""
        self.tank.stop()
        self.leds.off()
        self.buzzer.off()
        self.ultrasonic.stop()
        if self._ser.is_open:
            self._ser.close()
        print("[Arduino] Detenido y puerto cerrado.")

    # ── Propiedades de seguridad (API compatible con tensor_rt.py) ────────────

    @property
    def can_move_forward(self) -> bool:
        """True si el sensor delantero no detecta obstáculo."""
        return not self.ultrasonic.is_front_blocked

    @property
    def can_move_backward(self) -> bool:
        """True siempre (sin sensor trasero en el nuevo firmware)."""
        return True

    @property
    def can_turn(self) -> bool:
        """True si el robot puede girar (sensor despejado)."""
        return not self.ultrasonic.is_blocked

    # ── Helpers de conveniencia ───────────────────────────────────────────────

    def react_to_emotion(self, emotion: str, confidence: float = 1.0) -> list:
        """
        Reacciona a una emoción delegando al EmotionManager.
        Retorna la lista de Futures de los comandos enviados.
        """
        return self.emotions.apply_emotion(emotion, confidence)

    def display_sensor_info(self) -> None:
        """Muestra la distancia del sensor en el LCD (formateado)."""
        cm = self.ultrasonic.distance_cm
        if cm < 0:
            self.lcd.display_text("US: sin dato")
        else:
            self.lcd.display_text(f"US: {cm:.1f} cm")

    # ── Callback de obstáculo ─────────────────────────────────────────────────

    def _register_obstacle_watcher(self) -> None:
        """Registra un watcher que llama a self.on_obstacle cuando el sensor se bloquea."""
        observer = self.ultrasonic

        def _watcher(controller_id: str, payload: str) -> None:
            pass  # El estado ya es gestionado por UltrasonicObserver

        # Inyectamos el watcher directamente en el dispatch del observer
        # usando monkey-patch del método _handle_us
        original_handle_us = observer._handle_us

        def _patched_handle_us(ctrl_id: str, pl: str) -> None:
            was_blocked = observer.is_blocked
            original_handle_us(ctrl_id, pl)
            now_blocked = observer.is_blocked
            cm = observer.distance_cm

            # Reacción automática de bajo nivel (zumbido) vía EmotionManager
            if now_blocked:
                self.emotions.react_to_obstacle(cm)

            # Reacción de alto nivel (callback definido por el usuario)
            if not was_blocked and now_blocked and self.on_obstacle is not None:
                try:
                    self.on_obstacle(cm)
                except Exception as e:
                    print(f"[Arduino] Error en on_obstacle callback: {e}")

        observer._handle_us = _patched_handle_us
