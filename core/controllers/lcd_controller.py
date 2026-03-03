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


class LcdController:

    MAX_CHARS = 16   # columnas del LCD (según PinDeclaration.h: LCD_COLS = 16)

    def __init__(self, port, verbose: bool = False):
        self._port    = port
        self._verbose = verbose

    # ── API pública ──────────────────────────────────────────────────────────

    def display_text(self, text: str, line: int = 0, col: int = 0) -> None:
        """
        Muestra texto en todos los LCDs.
        Los parámetros `line` y `col` se mantienen por compatibilidad con el código
        existente (tensor_rt.py, main.py) pero el firmware actual ignora line/col
        y siempre escribe desde (0, 0).
        El texto se trunca a MAX_CHARS caracteres.
        """
        try:
            if not text:
                text = " "
            safe = str(text)[:self.MAX_CHARS].replace('\n', ' ').replace('\r', '')
            self._send(safe)
        except Exception as e:
            print(f"[LCD] ERROR: {e}")

    def clear(self) -> None:
        """Limpia todos los LCDs (envía un espacio — cada escritura ya limpia)."""
        self.display_text(" ")

    def display_two_lines(self, top: str, bottom: str) -> None:
        """
        Muestra dos líneas. Como el firmware actual solo soporta una línea,
        se muestra 'top | bottom' truncado. Para soporte real de dos líneas
        extender el firmware con un separador.
        """
        combined = f"{top[:8]} {bottom[:7]}"
        self.display_text(combined)

    def display_emotion(self, emotion: str, confidence: float) -> None:
        """Atajo para mostrar la emoción detectada y su confianza."""
        self.display_text(f"{emotion[:10]} {confidence:.0%}")

    def display_distance(self, distance_cm: float) -> None:
        """Atajo para mostrar la lectura del sensor ultrasónico."""
        if distance_cm < 0:
            self.display_text("US: sin dato")
        else:
            self.display_text(f"US: {distance_cm:.1f} cm")

    # ── Interno ──────────────────────────────────────────────────────────────

    def _send(self, text: str) -> None:
        line = f"LCD:{text}"
        if self._verbose:
            print(f"[LCD] → {line}")
        self._port.send_line(line)
