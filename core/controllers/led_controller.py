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

    def __init__(self, port, controller_id: str = "LED_1", verbose: bool = False):
        self._port    = port
        self._id      = controller_id
        self._verbose = verbose

    # ── API pública ──────────────────────────────────────────────────────────

    def on(self) -> None:
        """Enciende todos los LEDs del controlador específico."""
        self._send("ON")

    def off(self) -> None:
        """Apaga todos los LEDs."""
        self._send("OFF")

    def blink(self) -> None:
        """Invierte el estado de todos los LEDs (toggle)."""
        self._send("BLINK")

    def set_color(self, r: int, g: int, b: int) -> None:
        """Establece el color de los LEDs (0-255)."""
        self._send(f"COLOR:{r},{g},{b}")

    def set_brightness(self, value: int) -> None:
        """Establece el brillo global (0-255)."""
        self._send(f"BRIGHTNESS:{value}")

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

    def _send(self, command: str) -> None:
        try:
            # Nuevo protocolo: {BASE_ID}:{SPECIFIC_ID}:{COMMAND}
            line = f"LED:{self._id}:{command}"
            if self._verbose:
                print(f"[LED] → {line}")
            self._port.send_line(line)
        except Exception as e:
            print(f"[LED] ERROR: {e}")

    # ── Unit Test ────────────────────────────────────────────────────────────

    def test_interface(self) -> bool:
        """
        Prueba la interfaz enviando comandos básicos.
        Retorna True si no hubo excepciones.
        """
        print(f"--- Testing LedController ({self._id}) ---")
        try:
            self.off()
            self.on()
            self.set_color(255, 0, 0)
            self.set_brightness(100)
            self.blink()
            print("[LED] Test interface OK")
            return True
        except Exception as e:
            print(f"[LED] Test interface FAILED: {e}")
            return False
