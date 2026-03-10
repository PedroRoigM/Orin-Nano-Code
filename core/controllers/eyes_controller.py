"""
eyes_controller.py
==================
Controla las pantallas oculares GC9A01 via Arduino (firmware ArduinoBoardFirmware).

Protocolo texto (newline-terminado, BASE_ID=EYE):

  EYE:EYE_<n>:ON                                          — enciende la pantalla
  EYE:EYE_<n>:OFF                                         — apaga la pantalla
  EYE:EYE_<n>:FILL:<r>,<g>,<b>                            — rellena toda la pantalla
  EYE:EYE_<n>:DRAW:<shape>,<r>,<g>,<b>,<bg_r>,<bg_g>,<bg_b>
      shape  : neutral | happy | sad
      r/g/b  : color del iris (0-255)
      bg_*   : color de fondo (0-255)
  EYE:EYE_<n>:MOVE:<x>,<y>                                — mueve mirada (−100..+100)

Respuesta del Arduino:
  EYE_<n>:READY:ok     — pantalla lista tras begin()
  EYE_<n>:EYE:ok       — ACK de cada comando

Flujo de uso normal:
    eyes.on()
    eyes.draw("neutral", 200, 200, 180)      # una vez al inicio / al cambiar emoción
    # cada frame:
    eyes.move(gx_int, gy_int)               # throttled a GAZE_UPDATE_HZ
    # al cambiar emoción:
    eyes.draw("happy", 100, 220, 80)        # enviado solo si algo cambió

Compatibilidad con BehaviorEngine (mismo signature que antes):
    eyes.update(gx_float, gy_float, emotion, iris_color_override=(r,g,b))
"""

import time
from typing import Optional
from concurrent.futures import Future

# Mapa emoción → shape del firmware (solo las que tienen shape propio)
_EMOTION_SHAPE: dict[str, str] = {
    "happiness": "happy",
    "sadness":   "sad",
}


class EyesController:
    """
    Controlador serial para las pantallas oculares GC9A01.

    Separa los comandos costosos (DRAW — recalcula iris) de los ligeros
    (MOVE — solo actualiza el target de interpolación en el firmware):
      · DRAW se envía únicamente cuando cambia la forma o el color.
      · MOVE se envía cada frame a ≤ GAZE_UPDATE_HZ Hz.
    """

    GAZE_UPDATE_HZ: int = 20   # el firmware ya interpola en cada loop()

    def __init__(self, port, controller_id: str = "EYE_1", verbose: bool = False) -> None:
        self._port          = port
        self._id            = controller_id
        self._verbose       = verbose
        self._last_move_t   = 0.0
        # Clave del último DRAW enviado — evita reenvíos redundantes
        self._last_draw_key: Optional[tuple] = None

    # ── API principal ─────────────────────────────────────────────────────────

    def on(self) -> Future:
        """Enciende la pantalla (Sleep-Out + Display-On)."""
        return self._send("ON")

    def off(self) -> Future:
        """Apaga la pantalla (Display-Off + Sleep-In)."""
        return self._send("OFF")

    def fill(self, r: int, g: int, b: int) -> Future:
        """Rellena toda la pantalla con un color sólido."""
        return self._send(f"FILL:{r},{g},{b}")

    def draw(self, shape: str = "neutral",
             r: int = 200, g: int = 200, b: int = 180,
             bg_r: int = 0, bg_g: int = 0, bg_b: int = 0) -> Optional[Future]:
        """
        Dibuja el ojo con la forma y colores indicados.
        Solo envía al Arduino si algo cambió respecto al último DRAW.

        shape : "neutral" | "happy" | "sad"
        r/g/b : color del iris (0-255)
        bg_*  : color de fondo (0-255), negro por defecto
        """
        key = (shape, r, g, b, bg_r, bg_g, bg_b)
        if key == self._last_draw_key:
            return None
        self._last_draw_key = key
        return self._send(f"DRAW:{shape},{r},{g},{b},{bg_r},{bg_g},{bg_b}")

    def move(self, gx: int, gy: int) -> Optional[Future]:
        """
        Actualiza el target de mirada (gx, gy ∈ −100..+100).
        Throttled a GAZE_UPDATE_HZ Hz — el firmware interpola suavemente.
        """
        now = time.monotonic()
        if now - self._last_move_t < 1.0 / self.GAZE_UPDATE_HZ:
            return None
        self._last_move_t = now
        gx = max(-100, min(100, int(gx)))
        gy = max(-100, min(100, int(gy)))
        return self._send(f"MOVE:{gx},{gy}")

    def set_idle(self) -> Future:
        """Centra la mirada inmediatamente (ignora throttle)."""
        self._last_move_t = 0.0   # fuerza el envío
        return self._send("MOVE:0,0")

    # ── Compatibilidad con BehaviorEngine ────────────────────────────────────

    def update(
        self,
        gx: float,
        gy: float,
        emotion: str = "neutral",
        iris_color_override: Optional[tuple[int, int, int]] = None,
    ) -> None:
        """
        Interfaz compatible con BehaviorEngine.apply().

        gx / gy   : float −1.0..+1.0  → mapeado a −100..+100
        emotion   : nombre de la emoción (para seleccionar el shape)
        iris_color_override : color terapéutico del iris desde BEHAVIOR

        Internamente:
          · DRAW solo cuando cambia shape o color (barato en serial)
          · MOVE cada frame a ≤ GAZE_UPDATE_HZ Hz
        """
        r, g, b = iris_color_override if iris_color_override else (200, 200, 180)
        shape   = _EMOTION_SHAPE.get(emotion, "neutral")
        self.draw(shape, r, g, b)                              # deduplicado

        gx_i = int(max(-1.0, min(1.0, gx)) * 100)
        gy_i = int(max(-1.0, min(1.0, gy)) * 100)
        self.move(gx_i, gy_i)                                  # throttled

    # ── Interno ───────────────────────────────────────────────────────────────

    def _send(self, command: str) -> Future:
        """Envía EYE:{id}:{command}\\n al Arduino vía SharedPort."""
        line = f"EYE:{self._id}:{command}"
        if self._verbose:
            print(f"[EYE] → {line}")
        return self._port.send_line(line)

    # ── Unit Test ─────────────────────────────────────────────────────────────

    def test_interface(self) -> bool:
        """Ejercita todos los comandos. Retorna True si no hay excepciones."""
        print(f"--- Testing EyesController ({self._id}) ---")
        try:
            self.on().result(timeout=1.0)
            self.fill(0, 0, 128).result(timeout=1.0)
            self.draw("neutral", 200, 200, 180).result(timeout=1.0)
            self._last_move_t = 0.0
            self.move(50, 0).result(timeout=1.0)
            self._last_move_t = 0.0
            self.set_idle().result(timeout=1.0)
            self.off().result(timeout=1.0)
            print("[EYE] Test interface OK")
            return True
        except Exception as e:
            print(f"[EYE] Test interface FAILED: {e}")
            return False
