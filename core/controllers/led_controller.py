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
from concurrent.futures import Future

class LedController:

    def __init__(self, port, controller_id: str = "LED_1", verbose: bool = False):
        self._port    = port
        self._id      = controller_id
        self._verbose = verbose

    # ── API pública ──────────────────────────────────────────────────────────

    def on(self) -> Future:
        """Enciende todos los LEDs del controlador específico."""
        return self._send("ON")

    def off(self) -> Future:
        """Apaga todos los LEDs."""
        return self._send("OFF")

    def blink(self) -> Future:
        """Invierte el estado de todos los LEDs (toggle)."""
        return self._send("BLINK")

    def set_color(self, r: int, g: int, b: int) -> Future:
        """Establece el color de los LEDs (0-255)."""
        return self._send(f"COLOR:{r},{g},{b}")

    def set_brightness(self, value: int) -> Future:
        """Establece el brillo global (0-255)."""
        return self._send(f"BRIGHTNESS:{self._clamp(value)}")
    
    def _clamp(self, val: int, min_val: int = 0, max_val: int = 255) -> int:
        return max(min_val, min(max_val, int(val)))
    # ── Interno ──────────────────────────────────────────────────────────────

    def _send(self, command: str) -> Future:
        # Nuevo protocolo: {BASE_ID}:{SPECIFIC_ID}:{COMMAND}
        line = f"LED:{self._id}:{command}"
        if self._verbose:
            print(f"[LED] → {line}")
        return self._port.send_line(line)

    # ── Unit Test ────────────────────────────────────────────────────────────

    def test_interface(self) -> bool:
        """
        Prueba la interfaz enviando comandos básicos.
        Retorna True si no hubo excepciones (las promesas pueden no estar resueltas).
        """
        print(f"--- Testing LedController ({self._id}) ---")
        try:
            self.off().result(timeout=1.0)
            self.on().result(timeout=1.0)
            self.set_color(255, 0, 0).result(timeout=1.0)
            self.set_brightness(100).result(timeout=1.0)
            self.blink().result(timeout=1.0)
            print("[LED] Test interface OK (ACKs received)")
            return True
        except Exception as e:
            print(f"[LED] Test interface FAILED or TIMEOUT: {e}")
            return False
