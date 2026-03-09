"""
tensor_rt_orin.py
=================
Pipeline Jetson Orin Nano — ojos GC9A01 conectados DIRECTAMENTE por SPI.

Diferencias con tensor_rt.py:
  · GC9A01Controller (SPI directo a 40 MHz) reemplaza EyesController (serial→Arduino→SPI)
  · EyeRenderer: iris con degradado radial + textura + pupila + catchlight + párpado animado
  · Hilo daemon de render independiente → no bloquea el bucle de visión
  · Mantiene la última posición de mirada cuando se pierde la cara (sin salto al centro)
  · CONF_THRESHOLD bajado a 0.70 (MTCNN devuelve probs >= 0.9 internamente; 0.90 era redundante)
  · Fix: face_count == 0 cubre también el caso boxes != None pero todas bajo umbral

Hardware:
  Pantallas GC9A01 conectadas al conector de 40 pines de la Orin Nano:
    SDA → Pin 19   |  SCL → Pin 23
    CS izq → Pin 24 |  CS der → Pin 26
    DC   → Pin 18   |  RST → Pin 22   |  VCC → 3.3 V  |  GND → GND

Ejecutar (Jetson, dentro del venv del proyecto):
    cd /home/jetson/prueba && python3 core/tensor_rt_orin.py
"""

import cv2
import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
from facenet_pytorch import MTCNN
import torch
from time import time

from processing.emotion_color_mapper        import EmotionColorMapper
from controllers.arduino_controller         import ArduinoController
from controllers.gc9a01_controller          import GC9A01Controller
from controllers.camera_servo_controller    import CameraServoController
from companion_behavior                     import BehaviorEngine, BEHAVIOR

# ─────────────────────────────────────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────────────────────────────────────
FRAME_W, FRAME_H      = 640, 480
CONF_THRESHOLD        = 0.70
DETECT_EVERY_N_FRAMES = 2
OUTPUT_PATH           = "/home/jetson/prueba/output.mp4"

EMOTIONS = ["neutral", "happiness", "surprise", "sadness",
            "anger",   "disgust",   "fear",     "contempt"]

ARDUINO_PORT         = "/dev/ttyACM0"
ARDUINO_BAUD         = 9600
ULTRASONIC_THRESHOLD = 10.0

SERVO_PORT           = "/dev/ttyACM1"   # Puerto del Arduino con servos pan/tilt
SERVO_BAUD           = 9600

DEAD_ZONE_X = 60
TURN_SPEED  = 45
FWD_SPEED   = 40

EYE_FPS = 30   # FPS del hilo de render de los ojos

# ─────────────────────────────────────────────────────────────────────────────
# TensorRT — motor de inferencia de emociones
# ─────────────────────────────────────────────────────────────────────────────
TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
runtime    = trt.Runtime(TRT_LOGGER)

with open("/home/jetson/prueba/emotion.trt", "rb") as f:
    engine = runtime.deserialize_cuda_engine(f.read())

context = engine.create_execution_context()

input_shape  = (1, 1, 64, 64)
output_shape = (1, 8)
dtype        = np.float32

h_input  = cuda.pagelocked_empty(trt.volume(input_shape),  dtype=dtype)
h_output = cuda.pagelocked_empty(trt.volume(output_shape), dtype=dtype)
d_input  = cuda.mem_alloc(h_input.nbytes)
d_output = cuda.mem_alloc(h_output.nbytes)
stream   = cuda.Stream()

context.set_tensor_address("Input3",           int(d_input))
context.set_tensor_address("Plus692_Output_0", int(d_output))


def classify_emotion(face_roi: np.ndarray) -> tuple[str, float]:
    """Infiere la emoción de un recorte de cara usando TensorRT."""
    if face_roi.size == 0:
        return "unknown", 0.0
    gray    = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (64, 64)).astype(np.float32)
    np.copyto(h_input, resized.ravel())
    cuda.memcpy_htod_async(d_input, h_input, stream)
    context.execute_async_v3(stream_handle=stream.handle)
    cuda.memcpy_dtoh_async(h_output, d_output, stream)
    stream.synchronize()
    logits = h_output.copy()
    exp    = np.exp(logits - logits.max())
    probs  = exp / exp.sum()
    idx    = int(np.argmax(probs))
    return EMOTIONS[idx], float(probs[idx])


# ─────────────────────────────────────────────────────────────────────────────
# MTCNN — detector de caras en CUDA
# ─────────────────────────────────────────────────────────────────────────────
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"MTCNN device: {device}")

mtcnn = MTCNN(
    keep_all=True, device=device,
    min_face_size=60,
    thresholds=[0.7, 0.8, 0.9],
    post_process=False,
    select_largest=False,
)

emotionMapper = EmotionColorMapper()

# ─────────────────────────────────────────────────────────────────────────────
# _SpiEyesAdapter — une GC9A01Controller con BehaviorEngine
# ─────────────────────────────────────────────────────────────────────────────
class _SpiEyesAdapter:
    """
    Adapta GC9A01Controller a la interfaz que espera BehaviorEngine
    (update / set_idle).

    Diferencia clave respecto a la interfaz original:
      · set_idle() NO centra la mirada — mantiene la última posición conocida.
        Cuando se pierde la cara, los ojos se quedan quietos en su sitio en vez
        de saltar al centro. Solo cambia el color al tono terapéutico 'no_face'.
    """

    def __init__(self, ctrl: GC9A01Controller) -> None:
        self._ctrl        = ctrl
        self._last_gaze_x = 0.0
        self._last_gaze_y = 0.0

    def update(
        self,
        gaze_x:              float,
        gaze_y:              float,
        emotion:             str,
        confidence:          float = 1.0,
        iris_color_override: tuple | None = None,
    ) -> None:
        self._last_gaze_x = gaze_x
        self._last_gaze_y = gaze_y
        self._ctrl.update(gaze_x, gaze_y, emotion, confidence, iris_color_override)

    def set_idle(self) -> None:
        """Mantiene posición; aplica el color terapéutico de 'no_face'."""
        beh = BEHAVIOR.get("no_face", BEHAVIOR["neutral"])
        rgb = beh.get("eyes_rgb", (200, 200, 180))
        self._ctrl.update(
            self._last_gaze_x, self._last_gaze_y,
            "neutral", 1.0,
            iris_color_override=rgb,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Hardware
# ─────────────────────────────────────────────────────────────────────────────

# Ojos — SPI directo desde la Orin Nano
_gc9a01 = GC9A01Controller(target_fps=EYE_FPS, verbose=True)
_gc9a01.start()
eyes = _SpiEyesAdapter(_gc9a01)

# Arduino — motor, LEDs, LCD, buzzer (ya NO controla los ojos)
arduino = ArduinoController(ARDUINO_PORT, ARDUINO_BAUD, ULTRASONIC_THRESHOLD)
arduino.start()

# BehaviorEngine — pasa el adaptador SPI como controlador de ojos
behavior = BehaviorEngine(arduino=arduino, eyes=eyes)

# Servos pan/tilt de cámara
cam_servo = CameraServoController(SERVO_PORT, SERVO_BAUD, verbose=False)
cam_servo.center()

# ─────────────────────────────────────────────────────────────────────────────
# Callback de obstáculo ultrasónico
# ─────────────────────────────────────────────────────────────────────────────
def _on_obstacle(cm: float) -> None:
    arduino.tank.stop()
    arduino.leds.blink()
    arduino.buzzer.react_to_obstacle(cm, ULTRASONIC_THRESHOLD)
    print(f"[Obstacle] {cm:.1f} cm — motor detenido")

arduino.on_obstacle = _on_obstacle

# Startup
arduino.lcd.display_two_lines("Robot medico", "Listo :)")
arduino.buzzer.startup_chime()
arduino.leds.on()

# ─────────────────────────────────────────────────────────────────────────────
# Tira de LEDs NeoPixel (stub — activar cuando el firmware lo soporte)
# ─────────────────────────────────────────────────────────────────────────────
def set_led_strip(r: int, g: int, b: int) -> None:
    pass  # arduino.led_strip.set_color(r, g, b) cuando el firmware lo soporte

# ─────────────────────────────────────────────────────────────────────────────
# Cámara CSI via GStreamer
# ─────────────────────────────────────────────────────────────────────────────
GST_PIPELINE = (
    "nvarguscamerasrc sensor_id=0 ! "
    "video/x-raw(memory:NVMM),width=640,height=480,framerate=30/1,format=NV12 ! "
    "nvvidconv flip-method=0 ! video/x-raw,format=BGRx ! "
    "videoconvert ! video/x-raw,format=BGR ! appsink drop=1 max-buffers=1"
)

cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
if not cap.isOpened():
    raise RuntimeError("No se pudo abrir la cámara CSI. Verifica el pipeline GStreamer.")

out = cv2.VideoWriter(OUTPUT_PATH, cv2.VideoWriter_fourcc(*"mp4v"),
                      15, (FRAME_W, FRAME_H))

# ─────────────────────────────────────────────────────────────────────────────
# Estado
# ─────────────────────────────────────────────────────────────────────────────
boxes           = None
det_probs       = None
frame_count     = 0
fps_time        = time()
fps             = 0.0
FRAME_CX        = FRAME_W // 2
FRAME_CY        = FRAME_H // 2
current_emotion = "neutral"
current_conf    = 0.0

print("Grabando... Pulsa Ctrl+C para detener.")

# ─────────────────────────────────────────────────────────────────────────────
# Lógica de movimiento
# ─────────────────────────────────────────────────────────────────────────────
def drive_toward_face(face_cx: int, emotion: str) -> None:
    if behavior.motor_should_pause(emotion):
        arduino.tank.stop()
        return

    error_x = face_cx - FRAME_CX
    if abs(error_x) <= DEAD_ZONE_X:
        if arduino.can_move_forward:
            arduino.tank.forward(FWD_SPEED)
        else:
            arduino.tank.stop()
    elif error_x < 0:
        if arduino.can_turn:
            arduino.tank.turn_left(TURN_SPEED)
        else:
            arduino.tank.stop()
    else:
        if arduino.can_turn:
            arduino.tank.turn_right(TURN_SPEED)
        else:
            arduino.tank.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Bucle principal
# ─────────────────────────────────────────────────────────────────────────────
try:
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("No frame received.")
            break

        frame_count += 1

        if frame_count % 30 == 0:
            fps = 30 / (time() - fps_time)
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

                colors    = emotionMapper.get_color_dict(emotion, confidence=emo_conf)
                box_color = colors["dominant_rgb"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(frame, f"{emotion} {emo_conf:.0%}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, box_color, 2)

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

                    drive_toward_face(face_cx, emotion)
                    cam_servo.track(face_cx, face_cy, FRAME_W, FRAME_H)

        if face_count == 0:
            arduino.tank.stop()
            cam_servo.update_idle()
            behavior.apply("no_face")
            r, g, b = behavior.get_led_strip_color("no_face")
            set_led_strip(r, g, b)
            current_emotion = "no_face"
            current_conf    = 0.0

        # Diagnóstico cada 30 frames
        if frame_count % 30 == 0:
            n_raw = len(boxes) if boxes is not None else 0
            print(f"[Det] frame={frame_count} raw={n_raw} passed={face_count} "
                  f"fps={fps:.0f} emotion={current_emotion} conf={current_conf:.0%}")

        # HUD
        hud = (f"FPS:{fps:.0f}  Faces:{face_count}  "
               f"US:{arduino.ultrasonic.distance_cm:.0f}cm  {current_emotion}")
        cv2.putText(frame, hud, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        out.write(frame)

        try:
            cv2.imshow("Emotion Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        except Exception:
            pass  # SSH sin display

except KeyboardInterrupt:
    print("\nDetenido por el usuario.")

finally:
    _gc9a01.stop()
    cam_servo.close()
    arduino.stop()
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Vídeo guardado en {OUTPUT_PATH}")
