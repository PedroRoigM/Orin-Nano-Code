"""
eyes_controller.py
==================
Controla las pantallas oculares GC9A01 conectadas al Arduino
(firmware eyes_test.ino).

Protocolo texto (newline-terminado) — formato EYE:EYES_1:gx,gy,r,g,b:

  EYE:EYES_1:<gx>,<gy>,<r>,<g>,<b>\\n
      Actualiza posición Y color del iris en un único comando.
      · gx, gy: enteros −100..+100 (gaze normalizado −1..+1 × 180, clampeado).
      · r, g, b: enteros 0-255.
      · Enviado a GAZE_UPDATE_HZ Hz.
      Respuesta: EYES_1:EYE:ok

Ejemplo de uso:
    eyes = EyesController(shared_port, verbose=True)
    eyes.update(gaze_x=0.3, gaze_y=-0.1, emotion="sadness",
                iris_color_override=(255, 165, 50))
    eyes.set_idle()
"""

import time
from typing import Optional
from concurrent.futures import Future

class EyesController:
    """
    Controlador serial para las pantallas oculares GC9A01 gestionadas por Arduino.

    Interfaz compatible con GC9A01Controller (intercambiable):
      .update(gx, gy, r, g, b)
      .set_idle()
    """

    GAZE_UPDATE_HZ: int = 30   # máx. actualizaciones/s

    def __init__(self, port, controller_id: str = "EYE_1", verbose: bool = False) -> None:
        self._port        = port
        self._id          = controller_id
        self._verbose     = verbose
        self._last_gaze_t = 0.0
        self._last_gx     = 0
        self._last_gy     = 0

    # ── API pública ───────────────────────────────────────────────────────────

    def update(
        self,
        gx: float,
        gy: float,
        emotion: str = "neutral",
        iris_color_override: Optional[tuple[int, int, int]] = None
    ) -> Optional[Future]:
        """
        Envía posición + color al Arduino a ≤ GAZE_UPDATE_HZ Hz.
        gx, gy: float -1.0..1.0 (mapeado a -100..100)
        """
        now = time.monotonic()
        if now - self._last_gaze_t < 1.0 / self.GAZE_UPDATE_HZ:
            return None
        self._last_gaze_t = now

        # Convertir float -1..1 a int -100..100 per protocol
        gx_val = int(max(-1.0, min(1.0, gx)) * 100)
        gy_val = int(max(-1.0, min(1.0, gy)) * 100)

        self._last_gx = gx_val
        self._last_gy = gy_val

        # Obtener color (usar override o fallback a algo)
        # Nota: EyesController no debería conocer BEHAVIOR, por lo que 
        # iris_color_override es obligatorio o usamos un default.
        r, g, b = iris_color_override if iris_color_override else (200, 200, 180)

        return self._send(f"{gx_val},{gy_val},{r},{g},{b}")

    def set_idle(self) -> Future:
        """Centra la mirada."""
        return self._send(f"0,0,200,200,180")

    def set_color(self, r: int, g: int, b: int) -> Future:
        """Actualiza solo el color del iris."""
        return self._send(f"COLOR:{r},{g},{b}")

    def set_shape(self, shape: str) -> Future:
        """Establece la forma de la pupila (circle, star, smiley, x)."""
        return self._send(f"SHAPE:{shape}")

    # ── Interno ───────────────────────────────────────────────────────────────

    def _send(self, command: str) -> Future:
        """Envía EYE:{id}:command\\n al Arduino."""
        line = f"EYE:{self._id}:{command}"
        if self._verbose:
            print(f"[EYE] → {line}")
        return self._port.send_line(line)

    # ── Unit Test ────────────────────────────────────────────────────────────

    def test_interface(self) -> bool:
        """
        Prueba la interfaz enviando comandos básicos.
        Retorna True si no hubo excepciones (las promesas pueden no estar resueltas).
        """
        print(f"--- Testing EyesController ({self._id}) ---")
        try:
            self.set_idle().result(timeout=1.0)
            self.set_color(255, 255, 0).result(timeout=1.0)
            self.set_shape("star").result(timeout=1.0)
            print("[EYE] Test interface OK (ACKs received)")
            return True
        except Exception as e:
            print(f"[EYE] Test interface FAILED or TIMEOUT: {e}")
            return False
