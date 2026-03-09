"""
tank_controller.py
==================
Controla el motor de movimiento conectado al Arduino (nuevo firmware ArduinoBoardFirmware).

Protocolo texto (newline-terminado):
  MOT:FWD,<0-255>\n   → avanzar a velocidad dada
  MOT:REV,<0-255>\n   → retroceder a velocidad dada
  MOT:STOP,0\n        → detener

Velocidad: 0-255 (nativo del firmware).
El código legacy usa valores 1-127; estos siguen siendo válidos
(pasan a la placa como velocidad reducida, sin errores).

Firmware actual: un solo MotorController (MOT_1).
Para control independiente de ruedas izquierda/derecha (tanque real con
differential drive) extender el firmware con MOT_L y MOT_R como tipos
separados, y actualizar turn_left/turn_right en este módulo.

Respuesta del Arduino:
  MOT_1:DIR:FWD,SPD:150
  MOT_1:STATE:STOP
"""


def _clamp(v: int, lo: int = 0, hi: int = 255) -> int:
    return max(lo, min(hi, int(v)))


class TankController:
    """
    Mantiene la misma API pública que el TankController original
    para no romper tensor_rt.py:
        arduino.tank.forward(speed)
        arduino.tank.backward(speed)
        arduino.tank.turn_left(speed)
        arduino.tank.turn_right(speed)
        arduino.tank.stop()
    """

    def __init__(self, port, controller_id: str = "MOT_1", verbose: bool = False):
        self._port    = port
        self._id      = controller_id
        self._verbose = verbose

    # ── API pública ──────────────────────────────────────────────────────────

    def stop(self, **_) -> None:
        """Detiene el motor."""
        self._send("STOP")

    def forward(self, speed: int = 100, **_) -> None:
        """Avanza. speed: 0-255."""
        self._send(f"FWD,{_clamp(speed)}")

    def backward(self, speed: int = 100, **_) -> None:
        """Retrocede. speed: 0-255."""
        self._send(f"REV,{_clamp(speed)}")

    def turn_left(self, speed: int = 100, **_) -> None:
        """
        Giro a la izquierda.
        Con el firmware actual (un motor), se aproxima con REV.
        """
        self._send(f"REV,{_clamp(speed)}")

    def turn_right(self, speed: int = 100, **_) -> None:
        """
        Giro a la derecha.
        Con el firmware actual (un motor), se aproxima con FWD.
        """
        self._send(f"FWD,{_clamp(speed)}")

    # ── Interno ──────────────────────────────────────────────────────────────

    def _send(self, command: str) -> None:
        try:
            # Nuevo protocolo: {BASE_ID}:{SPECIFIC_ID}:{COMMAND}
            line = f"MOT:{self._id}:{command}"
            if self._verbose:
                print(f"[MOT] → {line}")
            self._port.send_line(line)
        except Exception as e:
            print(f"[MOT] ERROR: {e}")

    # ── Unit Test ────────────────────────────────────────────────────────────

    def test_interface(self) -> bool:
        """
        Prueba la interfaz enviando comandos básicos.
        Retorna True si no hubo excepciones.
        """
        print(f"--- Testing TankController ({self._id}) ---")
        try:
            self.stop()
            self.forward(100)
            self.backward(100)
            self.turn_left(100)
            self.turn_right(100)
            self.stop()
            print("[MOT] Test interface OK")
            return True
        except Exception as e:
            print(f"[MOT] Test interface FAILED: {e}")
            return False
