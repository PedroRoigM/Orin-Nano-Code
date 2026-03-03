"""
gc9a01_controller.py
====================
Controlador para un par de pantallas TFT circulares GC9A01 (1.28", 240×240 px)
conectadas al Jetson Orin Nano vía SPI.

Cada pantalla representa un ojo del robot. Los ojos:
  · Siguen a la primera cara detectada (mirada suavizada)
  · Cambian de color según la emoción (transición suave)
  · Parpadean automáticamente (intervalo aleatorio 3-8 s)

Dependencias:
  spidev        (pip install spidev)
  Jetson.GPIO   (preinstalado en JetPack)
  numpy, cv2    (ya disponibles en el proyecto)

Integración con tensor_rt.py / tensor_rt_computer.py:

    from controllers.gc9a01_controller import GC9A01Controller

    eyes = GC9A01Controller()
    eyes.start()

    # Dentro del bucle, tras detectar primera cara:
    face_cx = (x1 + x2) / 2
    face_cy = (y1 + y2) / 2
    gaze_x  = (face_cx - FRAME_W / 2) / (FRAME_W / 2)   # -1..+1
    gaze_y  = (face_cy - FRAME_H / 2) / (FRAME_H / 2)   # -1..+1
    eyes.update(gaze_x, gaze_y, emotion, emo_conf)

    # Si no hay cara:
    eyes.set_idle()

    # Al terminar:
    eyes.stop()

Para desarrollo en PC (sin hardware SPI/GPIO) usar gc9a01_tester.py.
"""

import math
import time
import random
import threading
import numpy as np
import cv2

# ─────────────────────────────────────────────────────────────────────────────
# Hardware opcional — solo disponible en Jetson Orin Nano con JetPack
# ─────────────────────────────────────────────────────────────────────────────
try:
    import spidev
    import Jetson.GPIO as GPIO
    _HW_AVAILABLE = True
except ImportError:
    _HW_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# Secuencia de inicialización GC9A01 (basada en el driver oficial Waveshare)
# Formato: (comando, datos_bytes, delay_ms)
# ─────────────────────────────────────────────────────────────────────────────
_INIT_SEQ = [
    (0xEF, b'',                                             0),
    (0xEB, b'\x14',                                         0),
    (0xFE, b'',                                             0),
    (0xEF, b'',                                             0),
    (0xEB, b'\x14',                                         0),
    (0x84, b'\x40',                                         0),
    (0x85, b'\xFF',                                         0),
    (0x86, b'\xFF',                                         0),
    (0x87, b'\xFF',                                         0),
    (0x88, b'\x0A',                                         0),
    (0x89, b'\x21',                                         0),
    (0x8A, b'\x00',                                         0),
    (0x8B, b'\x80',                                         0),
    (0x8C, b'\x01',                                         0),
    (0x8D, b'\x01',                                         0),
    (0x8E, b'\xFF',                                         0),
    (0x8F, b'\xFF',                                         0),
    (0xB6, b'\x00\x20',                                     0),
    (0x36, b'\x08',                                         0),  # Memory access
    (0x3A, b'\x05',                                         0),  # Pixel fmt: RGB565
    (0x90, b'\x08\x08\x08\x08',                            0),
    (0xBD, b'\x06',                                         0),
    (0xBC, b'\x00',                                         0),
    (0xFF, b'\x60\x01\x04',                                0),
    (0xC3, b'\x13',                                         0),
    (0xC4, b'\x13',                                         0),
    (0xC9, b'\x22',                                         0),
    (0xBE, b'\x11',                                         0),
    (0xE1, b'\x10\x0E',                                    0),
    (0xDF, b'\x21\x0C\x02',                               0),
    (0xF0, b'\x45\x09\x08\x08\x26\x2A',                  0),
    (0xF1, b'\x43\x70\x72\x36\x37\x6F',                  0),
    (0xF2, b'\x45\x09\x08\x08\x26\x2A',                  0),
    (0xF3, b'\x43\x70\x72\x36\x37\x6F',                  0),
    (0xED, b'\x1B\x0B',                                    0),
    (0xAE, b'\x77',                                         0),
    (0xCD, b'\x63',                                         0),
    (0x70, b'\x07\x07\x04\x0E\x0F\x09\x07\x08\x03',     0),
    (0xE8, b'\x34',                                         0),
    (0x62, b'\x18\x0D\x71\xED\x70\x70\x18\x0F\x71\xEF\x70\x70', 0),
    (0x63, b'\x18\x11\x71\xF1\x70\x70\x18\x13\x71\xF3\x70\x70', 0),
    (0x64, b'\x28\x29\xF1\x01\xF1\x00\x07',              0),
    (0x66, b'\x3C\x00\xCD\x67\x45\x45\x10\x00\x00\x00', 0),
    (0x67, b'\x00\x3C\x00\x00\x00\x01\x54\x10\x32\x98', 0),
    (0x74, b'\x10\x85\x80\x00\x00\x4E\x00',              0),
    (0x98, b'\x3E\x07',                                    0),
    (0x35, b'',                                             0),  # Tearing effect ON
    (0x21, b'',                                             0),  # Display inversion ON
    (0x11, b'',                                           120),  # Sleep out → esperar 120 ms
    (0x29, b'',                                            20),  # Display on → esperar 20 ms
]

# ─────────────────────────────────────────────────────────────────────────────
# Colores de iris por emoción (RGB — consistente con EmotionColorMapper)
# ─────────────────────────────────────────────────────────────────────────────
IRIS_COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "neutral":   (200, 200, 200),
    "happiness": ( 80, 220,   0),
    "surprise":  (  0, 220, 255),
    "sadness":   ( 30,  50, 180),
    "anger":     (220,  20,  20),
    "disgust":   ( 30, 130,  30),
    "fear":      (140,  20, 160),
    "contempt":  (150, 150,  30),
}

# Modificadores de forma del ojo por emoción
# squint: cierre parcial permanente del párpado superior (0–1)
# wide:   apertura extra del iris/pupila                 (0–1)
EYE_PARAMS: dict[str, dict[str, float]] = {
    "neutral":   {"squint": 0.00, "wide": 0.00},
    "happiness": {"squint": 0.18, "wide": 0.00},
    "surprise":  {"squint": 0.00, "wide": 0.18},
    "sadness":   {"squint": 0.12, "wide": 0.00},
    "anger":     {"squint": 0.25, "wide": 0.00},
    "disgust":   {"squint": 0.15, "wide": 0.00},
    "fear":      {"squint": 0.00, "wide": 0.15},
    "contempt":  {"squint": 0.10, "wide": 0.00},
}

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de animación
# ─────────────────────────────────────────────────────────────────────────────
MAX_GAZE_PX    = 30     # px máximos de desplazamiento del iris
LERP_GAZE      = 0.15   # factor de suavizado de mirada (0=sin mover, 1=instantáneo)
LERP_COLOR     = 0.05   # velocidad de transición de color de iris
BLINK_DURATION = 0.22   # segundos que dura un parpadeo completo
SPI_SPEED_HZ   = 40_000_000


# ─────────────────────────────────────────────────────────────────────────────
# EyeRenderer — genera imágenes 240×240 del ojo
# ─────────────────────────────────────────────────────────────────────────────
class EyeRenderer:
    """
    Genera imágenes NumPy (BGR, 240×240) que representan un ojo animado para
    la pantalla circular GC9A01.

    Anatomía renderizada:
      · Esclerótica (blanco cálido)
      · Iris con gradiente radial + textura de radios (color configurable)
      · Pupila
      · Destello de luz (catchlight)
      · Párpado superior animado (parpadeo + guiño por emoción)
      · Párpado inferior (solo en cierre completo)
      · Máscara circular (simula la pantalla redonda)

    Nota: internamente usa BGR (OpenCV). El controlador convierte a RGB565
    antes de enviar al display.
    """

    SIZE = 240

    def render(
        self,
        gaze_x:       float,
        gaze_y:       float,
        iris_color:   tuple[int, int, int],
        blink_factor: float = 1.0,
        squint:       float = 0.0,
        wide:         float = 0.0,
        mirrored:     bool  = False,
        color_is_bgr: bool  = False,
    ) -> np.ndarray:
        """
        Renderiza un frame del ojo.

        Args:
            gaze_x:       Mirada horizontal, -1 (izquierda) a +1 (derecha).
            gaze_y:       Mirada vertical, -1 (arriba) a +1 (abajo).
            iris_color:   Color del iris. Por defecto RGB; pasar color_is_bgr=True si es BGR.
            blink_factor: 1.0 = ojo abierto, 0.0 = ojo cerrado.
            squint:       Cierre parcial permanente del párpado (emoción).
            wide:         Apertura extra del iris (emoción sorpresa/miedo).
            mirrored:     True para el ojo derecho (refleja el destello).
            color_is_bgr: Si True, iris_color ya está en formato BGR.

        Returns:
            np.ndarray de forma (240, 240, 3), dtype=uint8, en formato BGR.
        """
        S  = self.SIZE
        cx = cy = S // 2
        img = np.zeros((S, S, 3), dtype=np.uint8)

        # Convertir color a BGR (formato interno)
        if color_is_bgr:
            c_bgr = iris_color
        else:
            c_bgr = (iris_color[2], iris_color[1], iris_color[0])

        # ── 1. Esclerótica ────────────────────────────────────────────────────
        cv2.circle(img, (cx, cy), 115, (242, 241, 238), -1, cv2.LINE_AA)

        # ── 2. Iris ───────────────────────────────────────────────────────────
        iris_r = int(76 + wide * 12)
        ox = int(np.clip(gaze_x * MAX_GAZE_PX, -MAX_GAZE_PX, MAX_GAZE_PX))
        oy = int(np.clip(gaze_y * MAX_GAZE_PX, -MAX_GAZE_PX, MAX_GAZE_PX))
        ic = (cx + ox, cy + oy)

        # Anillo limbal oscuro
        cv2.circle(img, ic, iris_r + 3, (18, 14, 10), -1, cv2.LINE_AA)

        # Gradiente radial: 8 círculos concéntricos (borde brillante → centro oscuro)
        for step in range(8, 0, -1):
            t = step / 8.0
            r = int(iris_r * t)
            f = 0.52 + 0.48 * t
            cv2.circle(img, ic, r, tuple(int(ch * f) for ch in c_bgr), -1, cv2.LINE_AA)

        # Textura: radios del iris
        dark = tuple(max(0, ch - 35) for ch in c_bgr)
        for deg in range(0, 360, 16):
            rad = math.radians(deg)
            r0  = int(iris_r * 0.42)
            r1  = int(iris_r * 0.91)
            p0  = (int(ic[0] + r0 * math.cos(rad)), int(ic[1] + r0 * math.sin(rad)))
            p1  = (int(ic[0] + r1 * math.cos(rad)), int(ic[1] + r1 * math.sin(rad)))
            cv2.line(img, p0, p1, dark, 1, cv2.LINE_AA)

        # ── 3. Pupila ─────────────────────────────────────────────────────────
        pupil_r = int(36 + wide * 8)
        cv2.circle(img, ic, pupil_r, (10, 8, 12), -1, cv2.LINE_AA)

        # ── 4. Destello (catchlight) ──────────────────────────────────────────
        cdx = -14 if not mirrored else 14
        cp  = (ic[0] + cdx, ic[1] - 14)
        cv2.circle(img, cp, 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(img, (cp[0] + 5, cp[1] + 5), 4, (255, 255, 255), -1, cv2.LINE_AA)

        # ── 5. Párpado superior ───────────────────────────────────────────────
        squint_drop = int(squint * 90)
        blink_drop  = int((1.0 - blink_factor) * 232)
        total_drop  = min(squint_drop + blink_drop, 234)
        eyelid_y    = (cy - 116) + total_drop

        if total_drop > 0:
            # Borde inferior del párpado con curva parabólica (más natural)
            pts = []
            for i in range(61):
                x   = int(cx - 118 + i * 236 / 60)
                t   = (x - cx) / 118.0
                crv = int(14 * (1.0 - t * t))
                pts.append([x, eyelid_y - crv])
            pts += [[cx + 122, -5], [cx - 122, -5]]
            cv2.fillPoly(img, [np.array(pts, np.int32)], (20, 16, 14))

        # ── 6. Párpado inferior (solo al cerrar completamente) ────────────────
        if blink_factor < 0.25:
            lt = 1.0 - blink_factor / 0.25
            ly = int(cy + 115 - lt * 42)
            lpts = []
            for i in range(61):
                x   = int(cx - 118 + i * 236 / 60)
                t   = (x - cx) / 118.0
                crv = int(10 * (1.0 - t * t))
                lpts.append([x, ly + crv])
            lpts += [[cx + 122, S + 5], [cx - 122, S + 5]]
            cv2.fillPoly(img, [np.array(lpts, np.int32)], (20, 16, 14))

        # ── 7. Máscara circular (simula la pantalla redonda) ──────────────────
        mask = np.zeros((S, S), dtype=np.uint8)
        cv2.circle(mask, (cx, cy), 118, 255, -1)
        result = np.zeros_like(img)
        result[mask > 0] = img[mask > 0]
        return result


# ─────────────────────────────────────────────────────────────────────────────
# GC9A01Controller — controlador hardware completo
# ─────────────────────────────────────────────────────────────────────────────
class GC9A01Controller:
    """
    Controlador de dos pantallas circulares GC9A01 para los ojos del robot R2.
    Requiere spidev y Jetson.GPIO (solo Jetson Orin Nano con JetPack).
    Para desarrollo en PC sin hardware usa gc9a01_tester.py.
    """

    DISPLAY_SIZE = 240

    def __init__(
        self,
        spi_bus:    int  = 0,
        cs_left:    int  = 0,    # /dev/spidev0.0
        cs_right:   int  = 1,    # /dev/spidev0.1
        dc_pin:     int  = 18,   # GPIO BOARD
        rst_pin:    int  = 22,
        bl_pin_l:   int  = 16,
        bl_pin_r:   int  = 15,
        target_fps: int  = 30,
        verbose:    bool = True,  # imprime estado SPI por terminal al cambiar emoción
    ):
        if not _HW_AVAILABLE:
            raise ImportError(
                "Faltan 'spidev' y/o 'Jetson.GPIO'. "
                "Para desarrollo en PC usa gc9a01_tester.py."
            )

        self._spi_bus  = spi_bus
        self._cs_l     = cs_left
        self._cs_r     = cs_right
        self._dc       = dc_pin
        self._rst      = rst_pin
        self._bl_l     = bl_pin_l
        self._bl_r     = bl_pin_r
        self._frame_dt = 1.0 / target_fps

        # Estado compartido (lock protege acceso desde hilo principal y de render)
        self._lock          = threading.Lock()
        self._gaze_x        = 0.0
        self._gaze_y        = 0.0
        self._tgt_gaze_x    = 0.0
        self._tgt_gaze_y    = 0.0
        self._emotion       = "neutral"
        self._iris_rgb      = list(IRIS_COLOR_RGB["neutral"])
        self._tgt_rgb       = list(IRIS_COLOR_RGB["neutral"])
        self._blink_start   = None
        self._blink_factor  = 1.0
        self._next_blink    = time.time() + _rand_blink_interval()

        self._verbose       = verbose
        self._last_emotion  = ""     # último estado logueado (para no repetir en cada frame)
        self._renderer = EyeRenderer()
        self._spi      = None
        self._running  = False
        self._thread   = None

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """Inicializa GPIO, SPI y ambas pantallas, luego arranca el hilo de render."""
        GPIO.setmode(GPIO.BOARD)
        for pin in (self._dc, self._rst, self._bl_l, self._bl_r):
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)

        self._spi = spidev.SpiDev()
        self._spi.open(self._spi_bus, self._cs_l)
        self._spi.max_speed_hz = SPI_SPEED_HZ
        self._spi.mode = 0
        self._spi.no_cs = True  # Gestionamos CS manualmente para dos pantallas

        # Necesitamos también controlar CS_R manualmente — configurar sus pines
        self._cs_l_gpio = 24   # BOARD pin 24 = SPI0_CS0
        self._cs_r_gpio = 26   # BOARD pin 26 = SPI0_CS1
        GPIO.setup(self._cs_l_gpio, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self._cs_r_gpio, GPIO.OUT, initial=GPIO.HIGH)

        self._reset()
        self._init_display(self._cs_l_gpio)
        self._init_display(self._cs_r_gpio)

        self._running = True
        self._thread  = threading.Thread(target=self._render_loop, daemon=True)
        self._thread.start()
        print("[GC9A01] Iniciado — dos pantallas oculares activas.")

    def stop(self) -> None:
        """Detiene el hilo de render, apaga las pantallas y libera recursos."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._spi:
            blank = np.zeros((self.DISPLAY_SIZE, self.DISPLAY_SIZE, 3), dtype=np.uint8)
            self._send_frame(blank, self._cs_l_gpio)
            self._send_frame(blank, self._cs_r_gpio)
            self._spi.close()
        GPIO.cleanup()
        print("[GC9A01] Detenido.")

    # ── API pública ───────────────────────────────────────────────────────────

    def update(
        self,
        gaze_x:              float,
        gaze_y:              float,
        emotion:             str,
        confidence:          float = 1.0,
        iris_color_override: tuple | None = None,
    ) -> None:
        """
        Actualiza la dirección de la mirada y la emoción del ojo.
        Llamar en cada frame desde tensor_rt.py tras detectar la primera cara.

        Args:
            gaze_x:              Posición horizontal normalizada (-1 izq, +1 der).
            gaze_y:              Posición vertical normalizada   (-1 arriba, +1 abajo).
            emotion:             Emoción detectada (clave de IRIS_COLOR_RGB).
            confidence:          Confianza del clasificador (0–1).
            iris_color_override: Si se proporciona una tupla RGB, anula el color por
                                 defecto de IRIS_COLOR_RGB. Usado por BehaviorEngine
                                 para aplicar la paleta terapéutica del robot médico.
        """
        with self._lock:
            self._tgt_gaze_x = float(np.clip(gaze_x, -1.0, 1.0))
            self._tgt_gaze_y = float(np.clip(gaze_y, -1.0, 1.0))
            self._emotion    = emotion
            if iris_color_override is not None:
                # Paleta terapéutica desde companion_behavior.py
                self._tgt_rgb = [int(c) for c in iris_color_override]
            elif emotion in IRIS_COLOR_RGB:
                self._tgt_rgb = list(IRIS_COLOR_RGB[emotion])

            # Log SPI cuando cambia la emoción (no en cada frame de gaze)
            if self._verbose and emotion != self._last_emotion:
                self._last_emotion = emotion
                r, g, b = self._tgt_rgb
                print(f"[SPI →] EYES:{emotion} | iris=({r},{g},{b}) | "
                      f"gaze=({self._tgt_gaze_x:+.2f},{self._tgt_gaze_y:+.2f})")

    def set_idle(self) -> None:
        """Centra la mirada cuando no hay cara detectada."""
        with self._lock:
            self._tgt_gaze_x = 0.0
            self._tgt_gaze_y = 0.0

    def trigger_blink(self) -> None:
        """Fuerza un parpadeo inmediato."""
        with self._lock:
            if self._blink_start is None:
                self._blink_start = time.time()

    # ── Bucle de render (hilo daemon) ─────────────────────────────────────────

    def _render_loop(self) -> None:
        while self._running:
            t0  = time.time()
            now = t0

            with self._lock:
                # Suavizar mirada
                self._gaze_x += (self._tgt_gaze_x - self._gaze_x) * LERP_GAZE
                self._gaze_y += (self._tgt_gaze_y - self._gaze_y) * LERP_GAZE

                # Transición suave de color
                for i in range(3):
                    self._iris_rgb[i] += (self._tgt_rgb[i] - self._iris_rgb[i]) * LERP_COLOR

                # Parpadeo automático
                if self._blink_start is None and now >= self._next_blink:
                    self._blink_start = now
                    self._next_blink  = now + BLINK_DURATION + _rand_blink_interval()

                # blink_factor según fase de animación
                bf = 1.0
                if self._blink_start is not None:
                    elapsed = (now - self._blink_start) / BLINK_DURATION
                    if   elapsed >= 1.0:  self._blink_start = None
                    elif elapsed < 0.30:  bf = 1.0 - elapsed / 0.30
                    elif elapsed < 0.40:  bf = 0.0
                    else:                 bf = (elapsed - 0.40) / 0.60
                self._blink_factor = bf

                # Snapshot de estado
                gx      = self._gaze_x
                gy      = self._gaze_y
                color   = tuple(int(c) for c in self._iris_rgb)
                bf_snap = self._blink_factor
                emotion = self._emotion

            params = EYE_PARAMS.get(emotion, EYE_PARAMS["neutral"])

            left  = self._renderer.render(gx, gy, color, bf_snap,
                                          params["squint"], params["wide"],
                                          mirrored=False)
            right = self._renderer.render(gx, gy, color, bf_snap,
                                          params["squint"], params["wide"],
                                          mirrored=True)

            self._send_frame(left,  self._cs_l_gpio)
            self._send_frame(right, self._cs_r_gpio)

            sleep = self._frame_dt - (time.time() - t0)
            if sleep > 0:
                time.sleep(sleep)

    # ── Hardware: SPI ─────────────────────────────────────────────────────────

    def _write_cmd(self, cmd: int, cs_gpio: int) -> None:
        GPIO.output(self._dc, GPIO.LOW)
        GPIO.output(cs_gpio, GPIO.LOW)
        self._spi.writebytes([cmd])
        GPIO.output(cs_gpio, GPIO.HIGH)

    def _write_data(self, data: bytes, cs_gpio: int) -> None:
        GPIO.output(self._dc, GPIO.HIGH)
        GPIO.output(cs_gpio, GPIO.LOW)
        CHUNK = 4096
        for i in range(0, len(data), CHUNK):
            self._spi.writebytes2(data[i:i + CHUNK])
        GPIO.output(cs_gpio, GPIO.HIGH)

    def _init_display(self, cs_gpio: int) -> None:
        for cmd, data, delay_ms in _INIT_SEQ:
            self._write_cmd(cmd, cs_gpio)
            if data:
                self._write_data(data, cs_gpio)
            if delay_ms:
                time.sleep(delay_ms / 1000.0)

    def _reset(self) -> None:
        GPIO.output(self._rst, GPIO.HIGH); time.sleep(0.05)
        GPIO.output(self._rst, GPIO.LOW);  time.sleep(0.10)
        GPIO.output(self._rst, GPIO.HIGH); time.sleep(0.05)

    def _set_window(self, x0: int, y0: int, x1: int, y1: int, cs_gpio: int) -> None:
        self._write_cmd(0x2A, cs_gpio)
        self._write_data(bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]), cs_gpio)
        self._write_cmd(0x2B, cs_gpio)
        self._write_data(bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]), cs_gpio)
        self._write_cmd(0x2C, cs_gpio)

    def _send_frame(self, img_bgr: np.ndarray, cs_gpio: int) -> None:
        """Convierte imagen BGR (OpenCV) a RGB565 y la envía al display vía SPI."""
        r = img_bgr[:, :, 2].astype(np.uint16)
        g = img_bgr[:, :, 1].astype(np.uint16)
        b = img_bgr[:, :, 0].astype(np.uint16)
        rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        pixels = rgb565.flatten().byteswap().tobytes()  # big-endian para GC9A01
        self._set_window(0, 0, 239, 239, cs_gpio)
        self._write_data(pixels, cs_gpio)


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades internas
# ─────────────────────────────────────────────────────────────────────────────

def _rand_blink_interval() -> float:
    return random.uniform(3.0, 8.0)
