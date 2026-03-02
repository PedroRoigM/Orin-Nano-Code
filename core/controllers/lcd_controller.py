from controllers.commandValues import CommandValues
from controllers.nodeValues import NodeValues


class LcdController:
    """
    Controla una pantalla LCD (típicamente 16x2 o 20x4) conectada al Arduino.

    Protocolo:
        display_text → [ CMD_LCD_TEXT,  NODE_LCD, line, col, ...ascii_bytes ]
        clear        → [ CMD_LCD_CLEAR, NODE_LCD, 0 ]

    `line` : fila de la pantalla (0 = primera, 1 = segunda, ...).
    `col`  : columna de inicio (0-based).

    El Arduino trunca el texto si supera el ancho de la pantalla.
    """

    MAX_LINE   = 3    # soporta hasta 4 filas (0-3)
    MAX_LENGTH = 20   # caracteres máximos por línea

    def __init__(self, port):
        self._port = port

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _check_line(self, line: int) -> None:
        if not (0 <= line <= self.MAX_LINE):
            raise ValueError(f"LCD line must be 0-{self.MAX_LINE}, got {line}")

    def _check_col(self, col: int) -> None:
        if not (0 <= col < self.MAX_LENGTH):
            raise ValueError(f"LCD column must be 0-{self.MAX_LENGTH - 1}, got {col}")

    def _check_text(self, text: str) -> None:
        if len(text) == 0:
            raise ValueError("LCD text must not be empty")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def display_text(self, text: str, line: int = 0, col: int = 0) -> None:
        """Escribe texto en la pantalla LCD en la fila y columna indicadas."""
        try:
            self._check_line(line)
            self._check_col(col)
            self._check_text(text)
            truncated = text[:self.MAX_LENGTH - col]
            ascii_bytes = [ord(c) for c in truncated]
            self._port.send_data([CommandValues.LCD_TEXT, NodeValues.LCD, line, col] + ascii_bytes)
        except Exception as e:
            print(f"[LCD] ERROR: {e}")

    def clear(self) -> None:
        """Limpia toda la pantalla LCD."""
        try:
            self._port.send_data([CommandValues.LCD_CLEAR, NodeValues.LCD, 0])
        except Exception as e:
            print(f"[LCD] ERROR: {e}")

    def display_two_lines(self, top: str, bottom: str) -> None:
        """Atajo para escribir dos líneas a la vez."""
        self.clear()
        self.display_text(top,    line=0)
        self.display_text(bottom, line=1)
