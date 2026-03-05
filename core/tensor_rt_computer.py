"""
tensor_rt_computer.py
=====================
Pipeline de desarrollo para PC/Mac — robot de acompañamiento médico.

Diferencias con tensor_rt.py (Jetson):
  · ONNX Runtime en lugar de TensorRT (compatible con macOS/Linux sin GPU)
  · Webcam estándar en lugar de cámara CSI
  · visual_eyes (SimulatedEyes): renderiza los ojos GC9A01 en pantalla (solo visual)
  · MockArduino: cuando no hay placa conectada, imprime TODOS los comandos
    seriales por terminal — incluyendo EYES/GAZE — para validar el comportamiento
    sin hardware. arduino.eyes = MockEyes replica la interfaz de EyesController.

Ventana de visualización:
  ┌──────────────────────────────┬───────────────────────────────┐
  │                              │  OJO IZQUIERDO                │
  │   Cámara  640×480            │  240×240                      │
  │                              ├───────────────────────────────┤
  │                              │  OJO DERECHO                  │
  │                              │  240×240                      │
  └──────────────────────────────┴───────────────────────────────┘
  Total: ~900×480 px

Ejecutar:
    cd core && .venv/bin/python3 tensor_rt_computer.py [--camera N]
"""

import sys
import argparse
import threading
import math
import time as _time
import cv2
import numpy as np
import onnxruntime as ort
from facenet_pytorch import MTCNN
import torch
from time import time

from processing.emotion_color_mapper  import EmotionColorMapper
from controllers.gc9a01_controller    import EyeRenderer, IRIS_COLOR_RGB, EYE_PARAMS
from controllers.eyes_controller      import EyesController
from companion_behavior               import BehaviorEngine, BEHAVIOR

# ─────────────────────────────────────────────────────────────────────────────
# Argumentos
# ─────────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Robot médico — modo PC")
parser.add_argument("--camera", type=int, default=0,
                    help="Índice de la cámara (0=built-in, 1=externa)")
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
FRAME_W, FRAME_H      = 640, 480
CONF_THRESHOLD        = 0.90
DETECT_EVERY_N_FRAMES = 2
OUTPUT_PATH           = "output.mp4"

EMOTIONS = ["neutral", "happiness", "surprise", "sadness",
            "anger",   "disgust",   "fear",     "contempt"]

ARDUINO_PORT         = "/dev/cu.usbmodem2101"   # Linux/Jetson; en Mac: "/dev/cu.usbmodemXXXX"
ARDUINO_BAUD         = 9600
ULTRASONIC_THRESHOLD = 10.0

EYE_DISPLAY_SIZE = 240   # tamaño del cuadrado donde se renderiza cada ojo

# ---------------------------------------------------------------------------
# ONNX Runtime — CoreML en Apple Silicon, CPU como fallback
# ---------------------------------------------------------------------------
providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
session     = ort.InferenceSession("core/emotion.onnx", providers=providers)
input_name  = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name


def classify_emotion(face_roi: np.ndarray) -> tuple[str, float]:
    if face_roi.size == 0:
        return "unknown", 0.0
    gray    = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (64, 64)).astype(np.float32)
    inp     = resized.reshape(1, 1, 64, 64)
    logits  = session.run([output_name], {input_name: inp})[0].flatten()
    exp     = np.exp(logits - logits.max())
    probs   = exp / exp.sum()
    idx     = int(np.argmax(probs))
    return EMOTIONS[idx], float(probs[idx])


# ---------------------------------------------------------------------------
# MTCNN — CPU para compatibilidad
# ---------------------------------------------------------------------------
device = torch.device("cpu")
print(f"MTCNN device: {device}")

mtcnn = MTCNN(
    keep_all=True, device=device,
    min_face_size=60,
    thresholds=[0.7, 0.8, 0.9],
    post_process=False,
    select_largest=False,
)

emotionMapper = EmotionColorMapper()

# ---------------------------------------------------------------------------
# MockArduino — simula la placa e imprime todos los comandos por terminal
# ---------------------------------------------------------------------------
class _PrintPort:
    """
    Puerto serial simulado para MockArduino.
    Redirige send_line() a stdout con el prefijo [SERIAL →].
    Permite reutilizar los controladores reales (EyesController, etc.)
    sin hardware, manteniendo toda la lógica del protocolo en un único lugar.
    """
    def send_line(self, line: str) -> None:
        print(f"[SERIAL →] {line}")


class MockArduino:
    """
    Reemplaza ArduinoController cuando no hay hardware conectado.
    Imprime en terminal cada comando que se enviaría al puerto serial,
    con el formato exacto del protocolo — {BASE}:{ID}:{CMD}.

    arduino.eyes usa EyesController real con _PrintPort, de modo que
    toda la lógica del protocolo vive en el controlador, no aquí.
    """

    class _Leds:
        def on(self):           print("[SERIAL →] LED:LED_1:ON")
        def off(self):          print("[SERIAL →] LED:LED_1:OFF")
        def blink(self):        print("[SERIAL →] LED:LED_1:BLINK")
        def flash_alert(self):  print("[SERIAL →] LED:LED_1:BLINK  ← alerta")

    class _Buzzer:
        def tone(self, freq: int, ms: int):
            print(f"[SERIAL →] BUZZ:BUZZ_1:{freq},{ms}")
        def off(self):
            print("[SERIAL →] BUZZ:BUZZ_1:OFF")
        def beep(self, freq: int = 1000, duration_ms: int = 200):
            print(f"[SERIAL →] BUZZ:BUZZ_1:{freq},{duration_ms}")
        def startup_chime(self):
            import time
            for freq in (440, 660, 880):
                print(f"[SERIAL →] BUZZ:BUZZ_1:{freq},120")
                time.sleep(0.14)
        def react_to_emotion(self, emotion: str):
            _TONES = {
                "neutral": (440, 100), "happiness": (880, 150),
                "surprise": (660, 200), "sadness": (220, 500),
                "anger": (150, 400),   "disgust": (180, 300),
                "fear": (800, 80),     "contempt": (300, 250),
            }
            f, d = _TONES.get(emotion, (440, 100))
            print(f"[SERIAL →] BUZZ:BUZZ_1:{f},{d}  ← emoción={emotion}")
        def react_to_obstacle(self, distance_cm: float, threshold_cm: float = 10.0):
            if distance_cm < 0 or distance_cm >= threshold_cm:
                return
            ratio = max(0.0, min(1.0, distance_cm / threshold_cm))
            freq  = int(500 + (1 - ratio) * 1500)
            dur   = int(50  + ratio * 150)
            print(f"[SERIAL →] BUZZ:BUZZ_1:{freq},{dur}  ← obstáculo {distance_cm:.1f}cm")

    class _Lcd:
        def display_text(self, text: str, line: int = 0, col: int = 0):
            print(f"[SERIAL →] LCD:LCD_1:{str(text)[:16]}")
        def display_two_lines(self, top: str, bottom: str):
            combined = f"{top[:8]} {bottom[:7]}"
            print(f"[SERIAL →] LCD:LCD_1:{combined}")
        def display_emotion(self, emotion: str, confidence: float):
            print(f"[SERIAL →] LCD:LCD_1:{emotion[:10]} {confidence:.0%}")
        def display_distance(self, cm: float):
            if cm < 0:
                print("[SERIAL →] LCD:LCD_1:US: sin dato")
            else:
                print(f"[SERIAL →] LCD:LCD_1:US: {cm:.1f} cm")
        def clear(self):
            print("[SERIAL →] LCD:LCD_1: ")

    class _Tank:
        def stop(self, **_):               print("[SERIAL →] MOT:MOT_1:STOP")
        def forward(self, speed, **_):     print(f"[SERIAL →] MOT:MOT_1:FWD,{speed}")
        def backward(self, speed, **_):    print(f"[SERIAL →] MOT:MOT_1:REV,{speed}")
        def turn_left(self, speed, **_):   print(f"[SERIAL →] MOT:MOT_1:REV,{speed}  ← giro izq")
        def turn_right(self, speed, **_):  print(f"[SERIAL →] MOT:MOT_1:FWD,{speed}  ← giro der")

    class _Ultrasonic:
        @property
        def distance_cm(self) -> float:      return -1.0
        @property
        def is_front_blocked(self) -> bool:  return False
        @property
        def is_blocked(self) -> bool:        return False

    def __init__(self) -> None:
        self.leds        = self._Leds()
        self.buzzer      = self._Buzzer()
        self.lcd         = self._Lcd()
        self.tank        = self._Tank()
        self.ultrasonic  = self._Ultrasonic()
        # EyesController real con puerto de impresión:
        # toda la lógica del protocolo (EYES:EYES_1:... / GAZE:EYES_1:...)
        # vive en EyesController, no duplicada aquí.
        self.eyes        = EyesController(_PrintPort(), verbose=False)
        self.on_obstacle = None

    @property
    def can_move_forward(self)  -> bool: return True
    @property
    def can_move_backward(self) -> bool: return True
    @property
    def can_turn(self)          -> bool: return True

    def start(self) -> None:
        print("[MockArduino] Iniciado — modo simulación serial activo.")

    def stop(self) -> None:
        print("[MockArduino] Detenido.")


# ---------------------------------------------------------------------------
# Arduino — real si está disponible, MockArduino en caso contrario
# ---------------------------------------------------------------------------
arduino: MockArduino | None = None
try:
    from controllers.arduino_controller import ArduinoController
    _hw = ArduinoController(ARDUINO_PORT, ARDUINO_BAUD, ULTRASONIC_THRESHOLD)
    _hw.start()

    def _on_obstacle(cm: float) -> None:
        _hw.tank.stop()
        _hw.leds.blink()
        _hw.buzzer.react_to_obstacle(cm, ULTRASONIC_THRESHOLD)
        print(f"[Obstacle] {cm:.1f} cm — motor detenido")

    _hw.on_obstacle = _on_obstacle
    _hw.lcd.display_two_lines("Robot medico", "Listo :)")
    _hw.buzzer.startup_chime()
    _hw.leds.on()
    arduino = _hw   # type: ignore[assignment]
    print("[Arduino] Hardware conectado en", ARDUINO_PORT)

except Exception as e:
    print(f"[Arduino] Hardware no disponible ({e})")
    print("[Arduino] Usando MockArduino — comandos seriales visibles en terminal.\n")
    arduino = MockArduino()
    arduino.start()


# ---------------------------------------------------------------------------
# SimulatedEyes — EyeRenderer con interfaz compatible con GC9A01Controller
# ---------------------------------------------------------------------------
class SimulatedEyes:
    """
    Renderizador visual de los ojos GC9A01 usando EyeRenderer + OpenCV.
    Solo visualización — NO emite comandos seriales.
    (Los comandos seriales los gestiona arduino.eyes: EyesController / MockEyes.)

    API:
      .update(gaze_x, gaze_y, emotion, confidence=1.0, iris_color_override=None)
      .set_idle()
      .get_frames() → (left_240x240, right_240x240)  para mostrar en pantalla.
    """

    LERP_GAZE  = 0.18
    LERP_COLOR = 0.08
    BLINK_DUR  = 0.22   # segundos

    def __init__(self) -> None:
        self._renderer   = EyeRenderer()
        self._lock       = threading.Lock()

        # Estado de mirada (suavizado)
        self._gaze_x     = 0.0
        self._gaze_y     = 0.0
        self._tgt_gaze_x = 0.0
        self._tgt_gaze_y = 0.0

        # Color de iris (suavizado)
        _default = list(IRIS_COLOR_RGB.get("neutral", (200, 200, 200)))
        self._iris_rgb   = _default[:]
        self._tgt_rgb    = _default[:]

        # Morfología del ojo
        self._squint     = 0.0
        self._wide       = 0.0
        self._tgt_squint = 0.0
        self._tgt_wide   = 0.0

        # Parpadeo automático
        self._blink_start  = None
        self._blink_factor = 1.0
        self._next_blink   = _time.time() + self._rand_blink()

    @staticmethod
    def _rand_blink() -> float:
        import random
        return random.uniform(3.0, 7.0)

    # ── API visual (actualizada en el bucle principal) ─────────────────────────

    def update(
        self,
        gaze_x:              float,
        gaze_y:              float,
        emotion:             str,
        confidence:          float = 1.0,
        iris_color_override: tuple | None = None,
    ) -> None:
        """
        Actualiza la mirada y el estado emocional del ojo simulado (solo visual).
        Usa los colores terapéuticos del BEHAVIOR por defecto; iris_color_override
        los sobreescribe si se proporciona.
        No emite ningún comando serial — eso lo hace arduino.eyes.
        """
        b = BEHAVIOR.get(emotion, BEHAVIOR["neutral"])
        with self._lock:
            self._tgt_gaze_x = float(np.clip(gaze_x, -1.0, 1.0))
            self._tgt_gaze_y = float(np.clip(gaze_y, -1.0, 1.0))
            self._tgt_squint = b.get("eyes_squint", 0.0)
            self._tgt_wide   = b.get("eyes_wide",   0.0)
            if iris_color_override is not None:
                self._tgt_rgb = [int(c) for c in iris_color_override]
            else:
                # Colores terapéuticos del BEHAVIOR (≠ FER+ estándar de IRIS_COLOR_RGB)
                rgb = b.get("eyes_rgb", list(IRIS_COLOR_RGB.get(emotion, (200, 200, 200))))
                self._tgt_rgb = [int(c) for c in rgb]

    def set_idle(self) -> None:
        """Centra la mirada y aplica el estado 'no_face' (solo visual)."""
        b = BEHAVIOR.get("no_face", BEHAVIOR["neutral"])
        with self._lock:
            self._tgt_gaze_x = 0.0
            self._tgt_gaze_y = 0.0
            self._tgt_squint = b.get("eyes_squint", 0.25)
            self._tgt_wide   = b.get("eyes_wide",   0.00)
            rgb = b.get("eyes_rgb", list(IRIS_COLOR_RGB.get("neutral", (200, 200, 180))))
            self._tgt_rgb = [int(c) for c in rgb]

    # ── Frames renderizados para el display ───────────────────────────────────

    def get_frames(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Devuelve (ojo_izquierdo, ojo_derecho) como ndarray BGR 240×240.
        Aplica suavizado de mirada, color e interpola morfología del párpado.
        Llamar en cada frame del bucle principal.
        """
        now = _time.time()
        with self._lock:
            # Suavizado de mirada
            self._gaze_x += (self._tgt_gaze_x - self._gaze_x) * self.LERP_GAZE
            self._gaze_y += (self._tgt_gaze_y - self._gaze_y) * self.LERP_GAZE

            # Suavizado de color
            for i in range(3):
                self._iris_rgb[i] += (self._tgt_rgb[i] - self._iris_rgb[i]) * self.LERP_COLOR

            # Suavizado de morfología
            self._squint += (self._tgt_squint - self._squint) * 0.12
            self._wide   += (self._tgt_wide   - self._wide)   * 0.12

            # Parpadeo automático
            if self._blink_start is None and now >= self._next_blink:
                self._blink_start = now
            if self._blink_start is not None:
                elapsed = now - self._blink_start
                half    = self.BLINK_DUR / 2
                self._blink_factor = max(0.0, 1.0 - abs(elapsed - half) / half * 2)
                if elapsed > self.BLINK_DUR:
                    self._blink_factor = 1.0
                    self._blink_start  = None
                    self._next_blink   = now + self._rand_blink()

            gx     = self._gaze_x
            gy     = self._gaze_y
            color  = tuple(int(c) for c in self._iris_rgb)
            bf     = self._blink_factor
            sq     = self._squint
            wd     = self._wide

        left  = self._renderer.render(gx, gy, color, bf, sq, wd, mirrored=False)
        right = self._renderer.render(gx, gy, color, bf, sq, wd, mirrored=True)
        return left, right


# ---------------------------------------------------------------------------
# Inicializar ojos y BehaviorEngine
# ---------------------------------------------------------------------------
# visual_eyes: renderizador visual en pantalla (puro OpenCV, sin serial)
# arduino.eyes: EyesController / MockEyes → gestiona los comandos SERIAL →
# BehaviorEngine usa arduino.eyes (no visual_eyes) para el comportamiento médico.
visual_eyes = SimulatedEyes()
behavior    = BehaviorEngine(arduino=arduino, eyes=arduino.eyes)

# ---------------------------------------------------------------------------
# Tira de LEDs NeoPixel — stub con log serial visible en PC
# ---------------------------------------------------------------------------
def set_led_strip(r: int, g: int, b: int) -> None:
    """
    Stub para la tira de LEDs NeoPixel (WS2812).
    En PC imprime el comando que se enviaría al firmware cuando esté disponible.
    En Jetson, reemplazar con: arduino.led_strip.set_color(r, g, b)
    """
    print(f"[SERIAL →] STRIP:RGB({r:3d},{g:3d},{b:3d})")

# ---------------------------------------------------------------------------
# Cámara — webcam estándar
# ---------------------------------------------------------------------------
cap = cv2.VideoCapture(args.camera)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
if not cap.isOpened():
    raise RuntimeError("No se pudo abrir la cámara.")

out = cv2.VideoWriter(OUTPUT_PATH, cv2.VideoWriter_fourcc(*"mp4v"),
                      15, (FRAME_W, FRAME_H))

# ---------------------------------------------------------------------------
# Disposición del panel de ojos en la ventana
# ---------------------------------------------------------------------------
# La ventana tiene 640 px (cámara) + 10 (gap) + 240 (ojos) = 890 px de ancho
# Los dos ojos se apilan verticalmente: 240+240=480 px (igual que el frame)
WIN_W    = FRAME_W + 10 + EYE_DISPLAY_SIZE  # 890
WIN_H    = FRAME_H                           # 480
EYE_X    = FRAME_W + 10                     # columna inicial del panel de ojos
EYE_L_Y  = 0                                # ojo izquierdo: fila 0
EYE_R_Y  = FRAME_H // 2                     # ojo derecho:   fila 240


def _draw_eye_bezel(canvas: np.ndarray, x: int, y: int, size: int = 240) -> None:
    """Dibuja el bisel circular alrededor del ojo (simula el marco de la pantalla)."""
    cx, cy, r = x + size // 2, y + size // 2, size // 2
    cv2.circle(canvas, (cx, cy), r + 6,  (70, 65, 68), -1)   # anillo exterior
    cv2.circle(canvas, (cx, cy), r + 2,  (18, 14, 16), -1)   # interior oscuro
    # Reflejo sutil en la parte superior
    pts = np.array([
        [cx - r // 2, cy - r + 4],
        [cx + r // 2, cy - r + 4],
        [cx + r // 3, cy - r + 16],
        [cx - r // 3, cy - r + 16],
    ], np.int32)
    overlay = canvas.copy()
    cv2.fillPoly(overlay, [pts], (100, 100, 110))
    cv2.addWeighted(overlay, 0.25, canvas, 0.75, 0, canvas)


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------
boxes           = None
det_probs       = None
frame_count     = 0
fps_time        = time()
fps             = 0.0
FRAME_CX        = FRAME_W // 2
FRAME_CY        = FRAME_H // 2
current_emotion = "neutral"
current_conf    = 0.0

print("Grabando... Pulsa 'q' para detener.")
cv2.namedWindow("Robot Medico", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Robot Medico", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------
try:
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("No frame received.")
            break

        frame_count += 1

        if frame_count % 120 == 0:
            fps = 120 / (time() - fps_time)
            fps_time = time()

        if frame_count % DETECT_EVERY_N_FRAMES == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes, det_probs = mtcnn.detect(rgb)

        face_count = 0

        if boxes is not None:
            for i, box in enumerate(boxes):
                if det_probs[i] < CONF_THRESHOLD:
                    continue
                x1 = max(0, int(box[0]))
                y1 = max(0, int(box[1]))
                x2 = min(FRAME_W, int(box[2]))
                y2 = min(FRAME_H, int(box[3]))
                if x2 <= x1 or y2 <= y1:
                    continue

                face_count += 1
                face_roi = frame[y1:y2, x1:x2]
                emotion, emo_conf = classify_emotion(face_roi)

                # Overlay visual en el frame
                colors    = emotionMapper.get_color_dict(emotion, confidence=emo_conf)
                box_color = colors["dominant_rgb"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(frame, f"{emotion} {emo_conf:.0%}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, box_color, 2)

                # Primera cara: comportamiento
                if face_count == 1:
                    current_emotion = emotion
                    current_conf    = emo_conf
                    face_cx = (x1 + x2) // 2
                    face_cy = (y1 + y2) // 2

                    changed = behavior.apply(
                        emotion, emo_conf,
                        face_cx=face_cx,
                        face_cy=face_cy,
                        frame_w=FRAME_W,
                        frame_h=FRAME_H,
                    )

                    if changed:
                        r, g, b = behavior.get_led_strip_color(emotion)
                        set_led_strip(r, g, b)
                        tag = BEHAVIOR.get(emotion, {}).get("log_tag", emotion)
                        print(f"[Behavior] {tag:10s} | conf={emo_conf:.0%} "
                              f"| strip=RGB({r},{g},{b})")

                    # Actualizar renderizador visual (SimulatedEyes, pantalla local)
                    gaze_x_v = (face_cx - FRAME_W / 2) / (FRAME_W / 2)
                    gaze_y_v = (face_cy - FRAME_H / 2) / (FRAME_H / 2)
                    visual_eyes.update(gaze_x_v, gaze_y_v, emotion)

        else:
            # Sin cara
            behavior.apply("no_face")
            visual_eyes.set_idle()
            r, g, b = behavior.get_led_strip_color("no_face")
            set_led_strip(r, g, b)
            current_emotion = "no_face"
            current_conf    = 0.0

        # ── Componer ventana final ────────────────────────────────────────────
        canvas = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)

        # Frame de cámara (izquierda)
        canvas[:FRAME_H, :FRAME_W] = frame

        # Ojos simulados (derecha) — renderizador visual local
        eye_l, eye_r = visual_eyes.get_frames()

        # Escalar ojos al tamaño de panel si es necesario
        if eye_l.shape[0] != EYE_DISPLAY_SIZE:
            eye_l = cv2.resize(eye_l, (EYE_DISPLAY_SIZE, EYE_DISPLAY_SIZE))
            eye_r = cv2.resize(eye_r, (EYE_DISPLAY_SIZE, EYE_DISPLAY_SIZE))

        # Bisel decorativo
        _draw_eye_bezel(canvas, EYE_X, EYE_L_Y, EYE_DISPLAY_SIZE)
        _draw_eye_bezel(canvas, EYE_X, EYE_R_Y, EYE_DISPLAY_SIZE)

        # Pegar ojos en el canvas
        canvas[EYE_L_Y:EYE_L_Y + EYE_DISPLAY_SIZE,
               EYE_X:EYE_X + EYE_DISPLAY_SIZE] = eye_l
        canvas[EYE_R_Y:EYE_R_Y + EYE_DISPLAY_SIZE,
               EYE_X:EYE_X + EYE_DISPLAY_SIZE] = eye_r

        # Separador vertical
        canvas[:, FRAME_W:FRAME_W + 10] = (40, 40, 40)

        # HUD cámara
        hw_mode = "HW" if not isinstance(arduino, MockArduino) else "SIM"
        us_val  = f"{arduino.ultrasonic.distance_cm:.0f}cm"
        hud = f"FPS:{fps:.0f}  Faces:{face_count}  US:{us_val}  [{hw_mode}] {current_emotion}"
        cv2.putText(canvas, hud,
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # Info emoción en panel de ojos
        b_info  = BEHAVIOR.get(current_emotion, BEHAVIOR["neutral"])
        tag_str = b_info.get("log_tag", current_emotion)
        led_str = b_info.get("led", "OFF")
        cv2.putText(canvas, tag_str,
                    (EYE_X + 4, EYE_R_Y + EYE_DISPLAY_SIZE - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.putText(canvas, f"conf={current_conf:.0%}  LED={led_str}",
                    (EYE_X + 4, EYE_R_Y + EYE_DISPLAY_SIZE - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1)

        out.write(canvas[:, :FRAME_W])   # solo el frame de cámara al vídeo

        cv2.imshow("Robot Medico", canvas)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print("\nDetenido.")

finally:
    if arduino is not None:
        arduino.stop()
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Vídeo guardado en {OUTPUT_PATH}")
