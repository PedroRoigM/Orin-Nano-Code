"""
camera_servo_controller.py
==========================
Controlador de servos pan/tilt para mantener la primera cara centrada en cámara.

Usa el MISMO puerto serial que el resto de controladores (SharedPort / _PrintPort).
Protocolo texto (nuevo firmware):
    NECK:SRV_1:<pan>,<tilt>\n   — ambos servos en un solo comando

Pipeline de control en track() (orden estricto):
  1. Stability gate      — ignora la cara hasta STABLE_FRAMES consecutivos
  2. EMA filter          — suaviza posición de cara (α=0.35, ~2 frames de retardo)
  3. Hysteresis dead zone — por eje, umbrales ENTER/HOLD independientes
  4. Idle→track lerp     — suaviza transición desde posición de barrido
  5. PD controller       — proporcional + derivativo (amortigua oscilación)
  6. Velocity cap        — limita Δ°/tick (pan 4°, tilt 2°)
  7. Hard clamp          — límites mecánicos garantizados

Uso:
    cam_servo = CameraServoController(port)   # port tiene send_line()
    cam_servo.center()

    # En el bucle cuando hay cara:
    cam_servo.track(face_cx, face_cy, frame_w=640, frame_h=480)

    # Cuando no hay cara:
    cam_servo.update_idle()

    cam_servo.close()   # centra y libera (el puerto lo cierra el propietario)
"""

import math
import time


# ── Parámetros mecánicos ──────────────────────────────────────────────────────
PAN_CENTER  = 90
TILT_CENTER = 90
PAN_MIN,  PAN_MAX  = 70, 110    # ±20° desde el centro
TILT_MIN, TILT_MAX = 80, 100    # ±10° desde el centro

# ── Temporización ─────────────────────────────────────────────────────────────
UPDATE_HZ   = 10     # máx. envíos/s — no saturar el bus serial compartido

# ── EMA en posición de cara ───────────────────────────────────────────────────
EMA_ALPHA   = 0.35   # factor de suavizado (0=sin filtro, 1=sin memoria).
                     # 0.35 → ~2 frames de retardo efectivo a 10 Hz.

# ── Zona muerta con histéresis (por eje) ──────────────────────────────────────
DEAD_ZONE_PAN_ENTER  = 0.10   # superar este umbral activa el eje pan
DEAD_ZONE_PAN_HOLD   = 0.04   # bajar de este umbral desactiva el eje pan
DEAD_ZONE_TILT_ENTER = 0.13   # tilt: rango mecánico más corto → zona mayor
DEAD_ZONE_TILT_HOLD  = 0.06

# ── Controlador PD ────────────────────────────────────────────────────────────
KP  = 9.0    # ganancia proporcional (°/unidad de error normalizado)
KD  = 2.0    # ganancia derivativa   (amortigua overshoot y oscilación)

# ── Límite de velocidad angular (°/tick a 10 Hz) ─────────────────────────────
MAX_DELTA_PAN   = 4.0   # → máx. 40°/s en pan
MAX_DELTA_TILT  = 2.0   # → máx. 20°/s en tilt (rango total solo 20°)

# ── Transición idle→track ─────────────────────────────────────────────────────
TRANSITION_FRAMES = 5   # ticks para lerp desde posición de barrido al objetivo.
                        # A 10 Hz = 500 ms de transición suave.

# ── Filtro de estabilidad de cara ─────────────────────────────────────────────
STABLE_FRAMES = 2       # frames consecutivos con cara antes de mover servos.
                        # Absorbe detecciones espurias de 1 frame de MTCNN.

# ── Barrido en espera ─────────────────────────────────────────────────────────
LERP_IDLE    = 0.05     # lerp physical→target en idle (muy lento)
SCAN_AMP_PAN = 5.0      # amplitud del barrido pan (°) — sutil
SCAN_FREQ    = 0.07     # Hz — un ciclo cada ~14 s (imperceptiblemente lento)


class CameraServoController:
    """
    Controlador PD de servos pan/tilt para seguimiento de cara.

    Acepta cualquier objeto con send_line(str) como puerto.
    No abre ni cierra serial — el ciclo de vida del puerto es del propietario.

    Parámetro baud ignorado (compatibilidad con tensor_rt_orin.py que pasa
    CameraServoController(port, baud, verbose=False) posicionalmente).
    """

    def __init__(self, port, baud=None, verbose: bool = False,
                 frame_w_default: int = 640,
                 frame_h_default: int = 480) -> None:
        self._port    = port
        self._verbose = verbose

        # Posición física actual
        self._pan  = float(PAN_CENTER)
        self._tilt = float(TILT_CENTER)

        # Objetivo del barrido senoidal en idle
        self._tgt_pan  = float(PAN_CENTER)
        self._tgt_tilt = float(TILT_CENTER)

        # Temporización
        self._last_t  = 0.0
        self._idle_t0 = time.monotonic()

        # Dedup de envío
        self._sent_pan  = -1
        self._sent_tilt = -1

        # EMA — inicializar al centro del frame para evitar spike en primera llamada
        self._ema_cx = float(frame_w_default / 2)
        self._ema_cy = float(frame_h_default / 2)

        # Histéresis por eje
        self._tracking_x = False
        self._tracking_y = False

        # PD — error anterior
        self._prev_err_x = 0.0
        self._prev_err_y = 0.0

        # Transición idle→track
        self._transition_frames     = 0
        self._transition_start_pan  = float(PAN_CENTER)
        self._transition_start_tilt = float(TILT_CENTER)

        # Estabilidad de cara
        self._stable_count = 0

    # ── API pública ───────────────────────────────────────────────────────────

    def center(self) -> None:
        """Mueve ambos servos al centro inmediatamente (sin filtros)."""
        self._pan = self._tgt_pan = float(PAN_CENTER)
        self._tilt = self._tgt_tilt = float(TILT_CENTER)
        self._send(PAN_CENTER, TILT_CENTER)

    def track(self, face_cx: int, face_cy: int,
              frame_w: int = 640, frame_h: int = 480) -> None:
        """
        Ajusta los servos para centrar la cara detectada.
        Llamar en cada frame cuando hay cara.

        Pipeline: stability gate → EMA → hysteresis → transition lerp →
                  PD control → velocity cap → hard clamp → _send.
        """
        now = time.monotonic()
        if now - self._last_t < 1.0 / UPDATE_HZ:
            return
        self._last_t = now
        self._idle_t0 = now   # resetear referencia de barrido

        # ── 1. Stability gate ─────────────────────────────────────────────────
        self._stable_count += 1
        if self._stable_count < STABLE_FRAMES:
            return   # cara aún no confirmada — no mover servos

        # ── 2. EMA en posición de cara ────────────────────────────────────────
        if self._stable_count == STABLE_FRAMES:
            # Primera vez que la cara es confirmada: reiniciar EMA al valor
            # actual para evitar el spike de la posición anterior de idle.
            self._ema_cx = float(face_cx)
            self._ema_cy = float(face_cy)
            # Registrar posición de inicio de transición
            self._transition_frames     = TRANSITION_FRAMES
            self._transition_start_pan  = self._pan
            self._transition_start_tilt = self._tilt
            self._prev_err_x = 0.0
            self._prev_err_y = 0.0
        else:
            self._ema_cx += EMA_ALPHA * (face_cx - self._ema_cx)
            self._ema_cy += EMA_ALPHA * (face_cy - self._ema_cy)

        # ── 3. Hysteresis dead zone ───────────────────────────────────────────
        raw_err_x = (self._ema_cx - frame_w / 2) / (frame_w / 2)
        raw_err_y = (self._ema_cy - frame_h / 2) / (frame_h / 2)

        if self._tracking_x:
            if abs(raw_err_x) < DEAD_ZONE_PAN_HOLD:
                self._tracking_x = False
        else:
            if abs(raw_err_x) >= DEAD_ZONE_PAN_ENTER:
                self._tracking_x = True

        if self._tracking_y:
            if abs(raw_err_y) < DEAD_ZONE_TILT_HOLD:
                self._tracking_y = False
        else:
            if abs(raw_err_y) >= DEAD_ZONE_TILT_ENTER:
                self._tracking_y = True

        err_x = raw_err_x if self._tracking_x else 0.0
        err_y = raw_err_y if self._tracking_y else 0.0

        if err_x == 0.0 and err_y == 0.0:
            self._prev_err_x = 0.0
            self._prev_err_y = 0.0
            return   # cara centrada — no enviar

        # ── 4. Idle→track transition lerp ─────────────────────────────────────
        if self._transition_frames > 0:
            # Calcular objetivo PD sin derivativo (prev_err aún no tiene sentido)
            pd_pan  = max(PAN_MIN,  min(PAN_MAX,  self._pan  - KP * err_x))
            pd_tilt = max(TILT_MIN, min(TILT_MAX, self._tilt - KP * err_y))

            # Interpolar desde posición de inicio de barrido hacia el objetivo PD
            alpha = (TRANSITION_FRAMES - self._transition_frames + 1) / TRANSITION_FRAMES
            alpha = min(alpha, 1.0)
            desired_pan  = self._transition_start_pan  + alpha * (pd_pan  - self._transition_start_pan)
            desired_tilt = self._transition_start_tilt + alpha * (pd_tilt - self._transition_start_tilt)

            self._transition_frames -= 1
            # Sembrar prev_err para que el primer tick PD tenga derivativa válida
            self._prev_err_x = err_x
            self._prev_err_y = err_y

        else:
            # ── 5. PD controller ──────────────────────────────────────────────
            d_err_x = err_x - self._prev_err_x
            d_err_y = err_y - self._prev_err_y
            self._prev_err_x = err_x
            self._prev_err_y = err_y

            desired_pan  = self._pan  - (KP * err_x + KD * d_err_x)
            desired_tilt = self._tilt - (KP * err_y + KD * d_err_y)

        # ── 6. Velocity cap ───────────────────────────────────────────────────
        delta_pan  = desired_pan  - self._pan
        delta_tilt = desired_tilt - self._tilt
        delta_pan  = max(-MAX_DELTA_PAN,  min(MAX_DELTA_PAN,  delta_pan))
        delta_tilt = max(-MAX_DELTA_TILT, min(MAX_DELTA_TILT, delta_tilt))

        # ── 7. Hard clamp a límites mecánicos ─────────────────────────────────
        self._pan  = max(PAN_MIN,  min(PAN_MAX,  self._pan  + delta_pan))
        self._tilt = max(TILT_MIN, min(TILT_MAX, self._tilt + delta_tilt))

        self._send(int(round(self._pan)), int(round(self._tilt)))

    def update_idle(self) -> None:
        """
        Cuando no hay cara: barrido senoidal suave en pan + retorno lento
        al centro en tilt. El robot parece buscar con calma.
        Resetea los filtros de tracking para la próxima detección.
        """
        # Resetear filtros — garantiza comportamiento limpio al re-detectar cara
        self._stable_count = 0
        self._tracking_x   = False
        self._tracking_y   = False

        now = time.monotonic()
        if now - self._last_t < 1.0 / UPDATE_HZ:
            return
        self._last_t = now

        elapsed = now - self._idle_t0

        # Pan: barrido senoidal suave alrededor del centro
        self._tgt_pan  = PAN_CENTER + SCAN_AMP_PAN * math.sin(2 * math.pi * SCAN_FREQ * elapsed)
        # Tilt: retorno gradual al centro
        self._tgt_tilt = TILT_CENTER

        self._pan  += (self._tgt_pan  - self._pan)  * LERP_IDLE
        self._tilt += (self._tgt_tilt - self._tilt) * LERP_IDLE

        self._send(int(round(self._pan)), int(round(self._tilt)))

    def close(self) -> None:
        """Centra los servos antes de cerrar. El puerto lo gestiona el propietario."""
        self.center()
        print("[CameraServo] Servos centrados.")

    # ── Interno ───────────────────────────────────────────────────────────────

    def _send(self, pan: int, tilt: int) -> None:
        """Envía solo si la posición cambió respecto al último envío."""
        if pan == self._sent_pan and tilt == self._sent_tilt:
            return
        self._sent_pan  = pan
        self._sent_tilt = tilt
        if self._verbose:
            print(f"[CameraServo] pan={pan}°  tilt={tilt}°")
        try:
            self._port.send_line(f"NECK:SRV_1:{pan},{tilt}")
        except Exception as e:
            print(f"[CameraServo] ERROR: {e}")
