from controllers.commandValues import CommandValues
from controllers.nodeValues import NodeValues


class LedController:
    """
    Controla tiras o grupos de LEDs RGB conectados al Arduino.

    Protocolo:
        set_color      → [ CMD_LED_COLOR,      NODE_LED, target, r, g, b ]
        set_brightness → [ CMD_LED_BRIGHTNESS, NODE_LED, target, brightness ]
        set_pattern    → [ CMD_LED_PATTERN,    NODE_LED, target, pattern_id ]

    `target` identifica el grupo de LEDs (0 = todos, 1..N = grupo específico).

    Patrones disponibles (definir en el Arduino):
        0 = apagado
        1 = color fijo
        2 = parpadeo
        3 = respiración
        4 = arco iris
        5 = pulso al ritmo
    """

    def __init__(self, port):
        self._port = port

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _check_color(self, value: int, name: str = "color") -> None:
        if not (0 <= value <= 255):
            raise ValueError(f"LED {name} must be 0-255, got {value}")

    def _check_brightness(self, value: int) -> None:
        if not (0 <= value <= 255):
            raise ValueError(f"LED brightness must be 0-255, got {value}")

    def _check_pattern(self, value: int) -> None:
        if not (0 <= value <= 5):
            raise ValueError(f"LED pattern must be 0-5, got {value}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_color(self, r: int, g: int, b: int, target: int = 0) -> None:
        """Establece el color RGB de un grupo de LEDs."""
        try:
            self._check_color(r, "red")
            self._check_color(g, "green")
            self._check_color(b, "blue")
            self._port.send_data([CommandValues.LED_COLOR, NodeValues.LED, target, r, g, b])
        except Exception as e:
            print(f"[LED] ERROR: {e}")

    def set_brightness(self, brightness: int, target: int = 0) -> None:
        """Establece el brillo global (0 = apagado, 255 = máximo)."""
        try:
            self._check_brightness(brightness)
            self._port.send_data([CommandValues.LED_BRIGHTNESS, NodeValues.LED, target, brightness])
        except Exception as e:
            print(f"[LED] ERROR: {e}")

    def set_pattern(self, pattern_id: int, target: int = 0) -> None:
        """Activa una animación predefinida en el Arduino."""
        try:
            self._check_pattern(pattern_id)
            self._port.send_data([CommandValues.LED_PATTERN, NodeValues.LED, target, pattern_id])
        except Exception as e:
            print(f"[LED] ERROR: {e}")

    def off(self, target: int = 0) -> None:
        """Apaga todos los LEDs del grupo."""
        self.set_brightness(0, target)
