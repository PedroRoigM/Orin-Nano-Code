from controllers.commandValues import CommandValues
from controllers.nodeValues import NodeValues


# Speed byte encoding (same byte range as the rest of the protocol):
#   127 = stop
#   128–254 = forward  (254 = full speed ahead)
#   1–126   = reverse  (1   = full speed reverse)
_STOP_BYTE = 127


def _fwd(magnitude: int) -> int:
    return 127 + max(1, min(127, magnitude))


def _rev(magnitude: int) -> int:
    return 127 - max(1, min(127, magnitude))


class TankController:
    """
    Controla 4 motores en 2 pares (izquierdo / derecho) como un tanque.
    Escribe a través de un SharedPort compartido.

    Protocolo enviado al Arduino:
        [ 0x40, CMD_TANK_DRIVE, NODE_TANK, all, left_byte, right_byte, 0x0D ]

    Velocidad (magnitude): entero 1-127, donde 127 es velocidad máxima.

    Decodificación en el Arduino:
        127        → parado
        128–254    → adelante  (254 = máxima velocidad)
        1–126      → atrás     (1   = máxima velocidad)
    """

    def __init__(self, port):
        self._port = port

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def stop(self, all: int = 1) -> None:
        self._send(all, _STOP_BYTE, _STOP_BYTE)

    def forward(self, speed: int = 50, all: int = 1) -> None:
        v = _fwd(speed)
        self._send(all, v, v)

    def backward(self, speed: int = 50, all: int = 1) -> None:
        v = _rev(speed)
        self._send(all, v, v)

    def turn_left(self, speed: int = 50, all: int = 1) -> None:
        """Gira a la izquierda: rueda derecha adelante, izquierda atrás."""
        self._send(all, _rev(speed), _fwd(speed))

    def turn_right(self, speed: int = 50, all: int = 1) -> None:
        """Gira a la derecha: rueda izquierda adelante, derecha atrás."""
        self._send(all, _fwd(speed), _rev(speed))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send(self, all: int, left: int, right: int) -> None:
        self._port.send_data([CommandValues.TANK_DRIVE, NodeValues.TANK, all, left, right])
