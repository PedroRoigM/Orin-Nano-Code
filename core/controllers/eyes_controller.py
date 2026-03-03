"""
eyes_controller.py
==================
Controla las pantallas oculares GC9A01 conectadas al Arduino
(firmware ArduinoBoardFirmware).

El Arduino gestiona las pantallas GC9A01 directamente por SPI local;
el Jetson le envía comandos de alto nivel vía el bus serial compartido.

Protocolo texto (newline-terminado):

  EYES:<emotion>,<r>,<g>,<b>,<squint>,<wide>\\n
      Actualiza color de iris y morfología del párpado.
      · squint y wide: enteros 0-100 (float × 100).
      · Solo se envía cuando cambia la emoción.

  GAZE:<gx>,<gy>\\n
      Actualiza la dirección de la mirada.
      · gx, gy: enteros −100..+100 (float × 100, normalizado −1..+1).
      · Rate-limitado a GAZE_UPDATE_HZ Hz para no saturar el bus a 9 600 baud.

Respuesta del Arduino (ignorada en Python, solo logging si verbose=True):
  EYES_ACK:ok
  GAZE_ACK:ok

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
    _FALLBACK_RGB    = BEHAVIOR.get("neutral", {}).get("eyes_rgb", (200, 200, 180))
    _FALLBACK_SQUINT = 0.0
    _FALLBACK_WIDE   = 0.0
except ImportError:
    BEHAVIOR      = {}
    _FALLBACK_RGB = (200, 200, 180)
    _FALLBACK_SQUINT = 0.0
    _FALLBACK_WIDE   = 0.0


class EyesController:
    """
    Controlador serial para las pantallas oculares GC9A01 gestionadas por Arduino.

    Interfaz compatible con GC9A01Controller (intercambiable):
      .update(gaze_x, gaze_y, emotion, confidence=1.0, iris_color_override=None)
      .set_idle()

    Todos los comandos se envían por el puerto serial compartido con el resto
    de controladores (LED, LCD, MOT, BUZZ).
    """

    GAZE_UPDATE_HZ: int = 20   # máx. actualizaciones de mirada/s
                               # 9 600 baud ≈ 960 B/s; GAZE:xxx,yyy\n ≈ 12 B → ~80 msg/s máximo

    def __init__(self, port, verbose: bool = False) -> None:
        """
        Args:
            port    : SharedPort — puerto serial compartido con otros controladores.
            verbose : Si True, imprime cada comando enviado como [SERIAL →] ...
        """
        self._port         = port
        self._verbose      = verbose
        self._last_emotion = ""    # última emoción enviada (para detectar cambio)
        self._last_gaze_t  = 0.0  # timestamp monotónico del último GAZE enviado

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
        Actualiza el estado de los ojos en el Arduino.

        · Si la emoción cambió → envía EYES:emotion,r,g,b,squint,wide
        · Cada ≥ 1/GAZE_UPDATE_HZ s → envía GAZE:gx,gy
        """
        # 1. EYES — solo cuando cambia la emoción ─────────────────────────────
        if emotion != self._last_emotion:
            self._last_emotion = emotion
            beh = BEHAVIOR.get(emotion, BEHAVIOR.get("neutral", {}))

            if iris_color_override is not None:
                r, g, b = (int(c) for c in iris_color_override)
            else:
                rgb = beh.get("eyes_rgb", _FALLBACK_RGB)
                r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])

            squint = int(beh.get("eyes_squint", _FALLBACK_SQUINT) * 100)
            wide   = int(beh.get("eyes_wide",   _FALLBACK_WIDE)   * 100)
            self._send("EYES", f"{emotion},{r},{g},{b},{squint},{wide}")

        # 2. GAZE — rate-limitado a GAZE_UPDATE_HZ Hz ─────────────────────────
        now = time.monotonic()
        if now - self._last_gaze_t >= 1.0 / self.GAZE_UPDATE_HZ:
            self._last_gaze_t = now
            gx = int(max(-100, min(100, round(gaze_x * 100))))
            gy = int(max(-100, min(100, round(gaze_y * 100))))
            self._send("GAZE", f"{gx},{gy}")

    def set_idle(self) -> None:
        """
        Pone los ojos en modo espera (sin cara detectada).
        Aplica el comportamiento 'no_face' del diccionario BEHAVIOR
        y centra la mirada.
        """
        if self._last_emotion != "no_face":
            self._last_emotion = "no_face"
            beh = BEHAVIOR.get("no_face", {})
            rgb    = beh.get("eyes_rgb", _FALLBACK_RGB)
            squint = int(beh.get("eyes_squint", 25) * 100)  # 0.25 → 25
            wide   = int(beh.get("eyes_wide",    0) * 100)
            r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
            self._send("EYES", f"no_face,{r},{g},{b},{squint},{wide}")

        # Centrar mirada en reposo (siempre, independiente del cambio de emoción)
        self._send("GAZE", "0,0")

    # ── Interno ───────────────────────────────────────────────────────────────

    def _send(self, cmd_type: str, payload: str) -> None:
        """Envía un comando al Arduino y lo loguea si verbose=True."""
        line = f"{cmd_type}:{payload}"
        if self._verbose:
            print(f"[SERIAL →] {line}")
        try:
            self._port.send_line(line)
        except Exception as e:
            print(f"[Eyes] ERROR al enviar '{line}': {e}")
