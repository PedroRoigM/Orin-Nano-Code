"""
led_controller.py
=================
Controla los LEDs conectados al Arduino (nuevo firmware ArduinoBoardFirmware).

Protocolo texto (newline-terminado):
  LED:ON\n    → enciende TODOS los LEDs registrados (LED_1, LED_2, LED_3)
  LED:OFF\n   → apaga todos
  LED:BLINK\n → invierte el estado de todos (toggle)

El Coordinator del Arduino hace broadcast a todos los LedController
registrados bajo el tipo "LED", por lo que el comando afecta a todos
simultáneamente. Para control individual de LEDs, extender el firmware
con tipos separados (LED_1, LED_2…).

Respuesta del Arduino (ignorada en Python, solo logging si verbose=True):
  LED_1:STATE:ON
  LED_2:STATE:OFF
  LED_3:STATE:BLINK
"""


class LedController:

    def __init__(self, port, verbose: bool = False):
        self._port    = port
        self._verbose = verbose

    # ── API pública ──────────────────────────────────────────────────────────

    def on(self) -> None:
        """Enciende todos los LEDs."""
        self._send("ON")

    def off(self) -> None:
        """Apaga todos los LEDs."""
        self._send("OFF")

    def blink(self) -> None:
        """Invierte el estado de todos los LEDs (toggle)."""
        self._send("BLINK")

    # ── Métodos de conveniencia para emociones ───────────────────────────────

    def flash_alert(self) -> None:
        """Parpadeo de alerta (usado cuando sensor detecta obstáculo)."""
        self._send("BLINK")

    def set_emotion(self, emotion: str) -> None:
        """
        Enciende/apaga LEDs según la emoción.
        Emociones positivas → ON, negativas → BLINK, neutral → OFF.
        """
        _BLINK   = {"anger", "fear", "disgust"}
        _OFF     = {"neutral", "sadness", "contempt"}
        if emotion in _BLINK:
            self.blink()
        elif emotion in _OFF:
            self.off()
        else:
            self.on()

    # ── Interno ──────────────────────────────────────────────────────────────

    def _send(self, payload: str) -> None:
        try:
            line = f"LED:{payload}"
            if self._verbose:
                print(f"[LED] → {line}")
            self._port.send_line(line)
        except Exception as e:
            print(f"[LED] ERROR: {e}")
