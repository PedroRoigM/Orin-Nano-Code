"""
lcd_controller.py
=================
Controla las pantallas LCD conectadas al Arduino (nuevo firmware ArduinoBoardFirmware).

Protocolo texto (newline-terminado):
  LCD:<texto>\n

El LcdController del Arduino hace clear() + setCursor(0,0) + print(texto)
antes de cada escritura, por lo que no es necesario enviar un clear explícito.
El Coordinator hace broadcast a TODOS los LCD registrados (LCD_1, LCD_2, LCD_3)
con el mismo texto simultáneamente.

Respuesta del Arduino:
  LCD_1:TEXT:<texto>
  LCD_2:TEXT:<texto>
  LCD_3:TEXT:<texto>

Nota: el firmware actual muestra el texto en la primera línea (cursor 0,0).
Para multi-línea extender el firmware con soporte de separador (p.ej. '|').
"""


from concurrent.futures import Future

class LcdController:

    MAX_CHARS = 16   # columnas del LCD (según PinDeclaration.h: LCD_COLS = 16)

    def __init__(self, port, controller_id: str = "LCD_1", verbose: bool = False):
        self._port    = port
        self._id      = controller_id
        self._verbose = verbose

    # ── API pública ──────────────────────────────────────────────────────────

    def display_text(self, text: str, line: int = 0, col: int = 0) -> Future:
        """
        Muestra texto en el LCD específico.
        Los parámetros `line` y `col` se mantienen por compatibilidad.
        """
        if not text:
            text = " "
        safe = str(text)[:self.MAX_CHARS].replace('\n', ' ').replace('\r', '')
        return self._send(safe)

    def clear(self) -> Future:
        """Limpia el LCD (envía un espacio — cada escritura ya limpia)."""
        return self.display_text(" ")

    def display_two_lines(self, top: str, bottom: str) -> Future:
        """
        Muestra dos líneas. Como el firmware actual solo soporta una línea,
        se muestra 'top | bottom' truncado.
        """
        combined = f"{top[:8]} {bottom[:7]}"
        return self.display_text(combined)

    # ── Interno ──────────────────────────────────────────────────────────────

    def _send(self, text: str) -> Future:
        # Nuevo protocolo: {BASE_ID}:{SPECIFIC_ID}:{COMMAND}
        line = f"LCD:{self._id}:{text}"
        if self._verbose:
            print(f"[LCD] → {line}")
        return self._port.send_line(line)

    # ── Unit Test ────────────────────────────────────────────────────────────

    def test_interface(self) -> bool:
        """
        Prueba la interfaz enviando comandos básicos.
        Retorna True si no hubo excepciones (las promesas pueden no estar resueltas).
        """
        print(f"--- Testing LcdController ({self._id}) ---")
        try:
            self.clear().result(timeout=1.0)
            self.display_text("Test Interface").result(timeout=1.0)
            print("[LCD] Test interface OK (ACKs received)")
            return True
        except Exception as e:
            print(f"[LCD] Test interface FAILED or TIMEOUT: {e}")
            return False
