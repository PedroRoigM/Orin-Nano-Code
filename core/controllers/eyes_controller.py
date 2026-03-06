"""
eyes_controller.py
==================
Controla las pantallas oculares GC9A01 conectadas al Arduino
(firmware eyes_test.ino).

Protocolo texto (newline-terminado) — formato EYE:EYES_1:gx,gy,r,g,b:

  EYE:EYES_1:<gx>,<gy>,<r>,<g>,<b>\\n
      Actualiza posición Y color del iris en un único comando.
      · gx, gy: enteros −100..+100 (gaze normalizado −1..+1 × 180, clampeado).
      · r, g, b: enteros 0-255.
      · Enviado a GAZE_UPDATE_HZ Hz.
      Respuesta: EYES_1:EYE:ok

Ejemplo de uso:
    eyes = EyesController(shared_port, verbose=True)
    eyes.update(gaze_x=0.3, gaze_y=-0.1, emotion="sadness",
                iris_color_override=(255, 165, 50))
    eyes.set_idle()
"""

import time
from typing import Optional

try:
    from companion_behavior import BEHAVIOR
    _FALLBACK_RGB = BEHAVIOR.get("neutral", {}).get("eyes_rgb", (200, 200, 180))
except ImportError:
    BEHAVIOR      = {}
    _FALLBACK_RGB = (200, 200, 180)


class EyesController:
    """
    Controlador serial para las pantallas oculares GC9A01 gestionadas por Arduino.

    Interfaz compatible con GC9A01Controller (intercambiable):
      .update(gaze_x, gaze_y, emotion, confidence=1.0, iris_color_override=None)
      .set_idle()
    """

    GAZE_UPDATE_HZ: int = 30   # máx. actualizaciones/s

    def __init__(self, port, verbose: bool = False) -> None:
        self._port        = port
        self._verbose     = verbose
        self._last_gaze_t = 0.0
        self._last_gx     = 0
        self._last_gy     = 0

    # ── API pública ───────────────────────────────────────────────────────────

    def update(
        self,
        gaze_x:              float,
        gaze_y:              float,
        emotion:             str,
        confidence:          float = 1.0,
        iris_color_override: Optional[tuple] = None,
    ) -> None:
        """
        Envía posición + color al Arduino a ≤ GAZE_UPDATE_HZ Hz.
        El color viene de iris_color_override o del diccionario BEHAVIOR.
        """
        now = time.monotonic()
        if now - self._last_gaze_t < 1.0 / self.GAZE_UPDATE_HZ:
            return
        self._last_gaze_t = now

        # Color: override terapéutico si se provee, si no BEHAVIOR
        if iris_color_override is not None:
            r, g, b = (int(c) for c in iris_color_override)
        else:
            beh = BEHAVIOR.get(emotion, BEHAVIOR.get("neutral", {}))
            rgb = beh.get("eyes_rgb", _FALLBACK_RGB)
            r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])

        # Amplificación 1.8× — movimientos faciales pequeños → movimiento visible
        gx = int(max(-100, min(100, round(gaze_x * 180))))
        gy = int(max(-100, min(100, round(gaze_y * 180))))
        self._last_gx = gx
        self._last_gy = gy

        self._send(f"{gx},{gy},{r},{g},{b}")

    def set_idle(self) -> None:
        """Centra la mirada y aplica el color 'no_face'."""
        now = time.monotonic()
        if now - self._last_gaze_t < 1.0 / self.GAZE_UPDATE_HZ:
            return
        self._last_gaze_t = now

        beh = BEHAVIOR.get("no_face", BEHAVIOR.get("neutral", {}))
        rgb = beh.get("eyes_rgb", _FALLBACK_RGB)
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
        self._send(f"{self._last_gx},{self._last_gy},{r},{g},{b}")

    # ── Interno ───────────────────────────────────────────────────────────────

    _COMPONENT_ID = "EYES_1"

    def _send(self, payload: str) -> None:
        """Envía EYE:EYES_1:payload\\n al Arduino."""
        line = f"EYE:{self._COMPONENT_ID}:{payload}"
        if self._verbose:
            print(f"[SERIAL →] {line}")
        try:
            self._port.send_line(line)
        except Exception as e:
            print(f"[Eyes] ERROR al enviar '{line}': {e}")
