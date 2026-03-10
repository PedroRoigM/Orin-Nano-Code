"""
tensor_rt.py
============
Pipeline principal Jetson Orin Nano — robot de acompañamiento médico.

Componentes integrados:
  · TensorRT          — clasificación de emociones en GPU (emotion.trt)
  · MTCNN             — detección de caras en CUDA
  · ArduinoController — LEDs, LCD, buzzer, motor DC, sensor ultrasónico
  · EyesController    — pantallas oculares GC9A01 vía Arduino (SERIAL)
  · BehaviorEngine    — diccionario de comportamiento médico editable
  · LED strip         — stub NeoPixel (activar cuando el firmware lo soporte)

Filosofía médica (ver companion_behavior.py):
  El robot NO refuerza emociones negativas. Usa colores y sonidos complementarios
  para calmar: tristeza→naranja cálido, ira→azul sereno, miedo→dorado cálido.
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
from controllers.camera_servo_controller    import CameraServoController
from companion_behavior                     import BehaviorEngine, BEHAVIOR

# ---------------------------------------------------------------------------
# Configuración — editar aquí para ajustar el comportamiento general
# ---------------------------------------------------------------------------
FRAME_W, FRAME_H = 640, 480
CONF_THRESHOLD   = 0.90           # Confianza mínima MTCNN para aceptar una cara
DETECT_EVERY_N_FRAMES = 2         # Cada N frames se lanza MTCNN (balance CPU/GPU)
OUTPUT_PATH = "/home/jetson/prueba/output.mp4"

EMOTIONS = ["neutral", "happiness", "surprise", "sadness",
            "anger",   "disgust",   "fear",     "contempt"]

# Arduino
ARDUINO_PORT         = "/dev/ttyACM0"
ARDUINO_BAUD         = 115200
ULTRASONIC_THRESHOLD = 10.0        # cm — detener motor y alertar por debajo de este valor

# Seguimiento de cara con el motor
DEAD_ZONE_X = 60                   # px de margen alrededor del centro (zona muerta)
TURN_SPEED  = 45                   # velocidad de giro (1-127)
FWD_SPEED   = 40                   # velocidad de avance (1-127)

# Ultrasónico — frecuencia de ping
ULTRASONIC_PING_HZ = 2             # pings por segundo (el firmware solo mide bajo petición)

# ---------------------------------------------------------------------------
# TensorRT — motor de inferencia de emociones
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# MTCNN — detector de caras
# ---------------------------------------------------------------------------
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"MTCNN device: {device}")

mtcnn = MTCNN(
    keep_all=True, device=device,
    min_face_size=60,
    thresholds=[0.7, 0.8, 0.9],
    post_process=False,
    select_largest=False,
)

# Mapper de colores para el overlay visual en el frame (colores FER+ estándar)
emotionMapper = EmotionColorMapper()

# ---------------------------------------------------------------------------
# Arduino — hub central de hardware
# ---------------------------------------------------------------------------
arduino = ArduinoController(ARDUINO_PORT, ARDUINO_BAUD, ULTRASONIC_THRESHOLD)
arduino.start()

# ---------------------------------------------------------------------------
# Callback de obstáculo ultrasónico
# ---------------------------------------------------------------------------
def _on_obstacle(cm: float) -> None:
    """
    Se ejecuta automáticamente cuando el sensor ultrasónico detecta un obstáculo.
    El robot se detiene, los LEDs parpadean y el buzzer emite una alerta.
    """
    arduino.tank.stop()
    arduino.leds.blink()
    arduino.buzzer.beep(800, 300)
    print(f"[Obstacle] Obstáculo detectado a {cm:.1f} cm — motor detenido")

arduino.on_obstacle = _on_obstacle

# ---------------------------------------------------------------------------
# BehaviorEngine — motor de comportamiento médico
# Los ojos se controlan a través de arduino.eyes (EyesController → SERIAL → Arduino → SPI)
# ---------------------------------------------------------------------------
behavior   = BehaviorEngine(arduino=arduino, eyes=arduino.eyes)
cam_servo  = CameraServoController(arduino._port, verbose=False)
cam_servo.center()

# Chime y estado visual de arranque
arduino.buzzer.startup_chime()
arduino.leds.on()

# ---------------------------------------------------------------------------
# Tira de LEDs NeoPixel/WS2812
# Envía el color terapéutico de BEHAVIOR a LED_1 y LED_2 via ArduinoBoardFirmware.
# Protocolo: LED:LED_1:COLOR:r,g,b  y  LED:LED_2:COLOR:r,g,b
# ---------------------------------------------------------------------------
def set_led_strip(r: int, g: int, b: int) -> None:
    """Establece el color de los LEDs (NeoPixel). Enviado por ARDUINO_PORT."""
    arduino.leds.set_color(r, g, b)

# ---------------------------------------------------------------------------
# Cámara CSI Jetson via GStreamer
# ---------------------------------------------------------------------------
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
_last_ping_t    = 0.0
_prev_had_face  = False   # para detectar transición no-cara → cara

print("Grabando... Pulsa Ctrl+C para detener.")
cv2.namedWindow("Emotion Detection", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Emotion Detection", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


# ---------------------------------------------------------------------------
# Lógica de movimiento
# ---------------------------------------------------------------------------
def drive_toward_face(face_cx: int, emotion: str) -> None:
    """
    Centra la primera cara detectada en el eje X girando o avanzando.

    Si el comportamiento médico de la emoción actual requiere que el motor
    se detenga (motor_pause=True en BEHAVIOR), el robot permanece quieto
    para transmitir presencia y calma — no persigue al paciente.
    """
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

        # Ping ultrasónico periódico (firmware solo mide bajo petición)
        now = time()
        if now - _last_ping_t >= 1.0 / ULTRASONIC_PING_HZ:
            arduino.ultrasonic.ping()
            _last_ping_t = now

        # FPS cada 30 frames
        if frame_count % 30 == 0:
            fps = 30 / (time() - fps_time)
            fps_time = time()

        # Detección de caras cada N frames
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

                # Overlay visual en el frame (colores FER+ estándar para visualización)
                colors    = emotionMapper.get_color_dict(emotion, confidence=emo_conf)
                box_color = colors["dominant_rgb"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(frame, f"{emotion} {emo_conf:.0%}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, box_color, 2)

                # Primera cara: comportamiento + movimiento
                if face_count == 1:
                    current_emotion = emotion
                    face_cx = (x1 + x2) // 2
                    face_cy = (y1 + y2) // 2

                    # Sonido de bienvenida al detectar la primera cara
                    if not _prev_had_face:
                        arduino.buzzer.beep(520, 80)   # Do (C5) suave — "te veo"
                    _prev_had_face = True

                    # Aplicar comportamiento médico (ojos siguen la cara cada frame;
                    # LEDs, buzzer y LCD solo cambian cuando la emoción es estable)
                    changed = behavior.apply(
                        emotion, emo_conf,
                        face_cx=face_cx,
                        face_cy=face_cy,
                        frame_w=FRAME_W,
                        frame_h=FRAME_H,
                    )

                    if changed:
                        # Actualizar tira de LEDs cuando el estado cambia
                        r, g, b = behavior.get_led_strip_color(emotion)
                        set_led_strip(r, g, b)
                        tag = BEHAVIOR.get(emotion, {}).get("log_tag", emotion)
                        print(f"[Behavior] {tag:10s} | conf={emo_conf:.0%} "
                              f"| strip=RGB({r},{g},{b})")

                    # Servo de cámara — sigue la cara
                    cam_servo.track(face_cx, face_cy, FRAME_W, FRAME_H)

                    # Movimiento del robot (respeta motor_pause del BEHAVIOR)
                    drive_toward_face(face_cx, emotion)

        else:
            # Sin cara: modo espera
            _prev_had_face = False
            arduino.tank.stop()
            cam_servo.update_idle()
            behavior.apply("no_face")
            r, g, b = behavior.get_led_strip_color("no_face")
            set_led_strip(r, g, b)
            current_emotion = "no_face"

        # HUD — información en el frame grabado
        hud_text = (f"FPS:{fps:.0f}  Faces:{face_count}  "
                    f"US:{arduino.ultrasonic.distance_cm:.0f}cm  {current_emotion}")
        cv2.putText(frame, hud_text,
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        out.write(frame)

        try:
            cv2.imshow("Emotion Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        except Exception:
            pass   # SSH sin display — ignorar

except KeyboardInterrupt:
    print("\nDetenido por el usuario.")

finally:
    cam_servo.close()
    arduino.stop()
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Vídeo guardado en {OUTPUT_PATH}")
