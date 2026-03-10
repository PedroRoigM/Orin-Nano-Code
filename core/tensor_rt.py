"""
tensor_rt.py
============
Pipeline principal Jetson Orin Nano — robot de acompañamiento médico.

Detección de caras:   SCRFD (InsightFace / FaceDetector) en GPU CUDA
Clasificación:        ONNX Runtime (emotion.onnx) con TensorrtExecutionProvider
Agregación:           Emoción de grupo ponderada por confianza (Counter multi-cara)
Cámara:               CSI via GStreamer (nvarguscamerasrc)
Hardware:             ArduinoController → LEDs, buzzer, motor, ojos, servo cuello

Filosofía médica (ver companion_behavior.py):
  El robot NO refuerza emociones negativas. Colores y sonidos complementarios
  para calmar: tristeza→naranja cálido, ira→azul sereno, miedo→dorado cálido.
"""

import os
import cv2
import numpy as np
import onnxruntime as ort
from collections import Counter
from time import time

from face_detector                          import FaceDetector
from processing.emotion_color_mapper        import EmotionColorMapper
from controllers.arduino_controller         import ArduinoController
from controllers.camera_servo_controller    import CameraServoController
from companion_behavior                     import BehaviorEngine, BEHAVIOR

# ---------------------------------------------------------------------------
# Configuración — editar aquí para ajustar el comportamiento general
# ---------------------------------------------------------------------------
FRAME_W, FRAME_H = 640, 480
CONF_THRESHOLD        = 0.70          # umbral de confianza SCRFD en el loop
DETECT_EVERY_N_FRAMES = 2             # cada N frames se lanza el detector
OUTPUT_PATH = "/home/jetson/prueba/output.mp4"

EMOTIONS = ["neutral", "happiness", "surprise", "sadness",
            "anger",   "disgust",   "fear",     "contempt"]

# Arduino
ARDUINO_PORT         = "/dev/ttyACM0"
ARDUINO_BAUD         = 115200
ULTRASONIC_THRESHOLD = 10.0           # cm — detener motor y alertar por debajo

# Seguimiento de cara con el motor
DEAD_ZONE_X = 60                      # px de margen alrededor del centro
TURN_SPEED  = 45                      # velocidad de giro (1-127)
FWD_SPEED   = 40                      # velocidad de avance (1-127)

# Ultrasónico — actualmente desactivado en el firmware (us1/us2 comentados)
# ULTRASONIC_PING_HZ = 2            # descomentar cuando el firmware lo reactive

# ---------------------------------------------------------------------------
# ONNX Runtime — clasificación de emociones
# Providers en orden de preferencia: TensorRT → CUDA → CPU
# ---------------------------------------------------------------------------
_model_path  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emotion.onnx")
_providers   = ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
session      = ort.InferenceSession(_model_path, providers=_providers)
_input_name  = session.get_inputs()[0].name
_output_name = session.get_outputs()[0].name


def classify_emotion(face_roi: np.ndarray) -> tuple[str, float]:
    """Infiere la emoción de un recorte de cara usando ONNX Runtime."""
    if face_roi.size == 0:
        return "unknown", 0.0
    gray    = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (64, 64)).astype(np.float32)
    inp     = resized.reshape(1, 1, 64, 64)
    logits  = session.run([_output_name], {_input_name: inp})[0].flatten()
    exp     = np.exp(logits - logits.max())
    probs   = exp / exp.sum()
    idx     = int(np.argmax(probs))
    return EMOTIONS[idx], float(probs[idx])


# ---------------------------------------------------------------------------
# FaceDetector — SCRFD via InsightFace (ctx_id=0 → GPU CUDA en Jetson)
# conf_threshold=0.3 permissivo; CONF_THRESHOLD filtra en el loop
# ---------------------------------------------------------------------------
detector     = FaceDetector(det_size=(FRAME_W, FRAME_H), conf_threshold=0.3, ctx_id=0)
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
    """Detiene el robot, parpadea LEDs y emite alerta sonora."""
    arduino.tank.stop()
    arduino.leds.blink()
    arduino.buzzer.beep(800, 300)
    print(f"[Obstacle] Obstáculo detectado a {cm:.1f} cm — motor detenido")

arduino.on_obstacle = _on_obstacle

# ---------------------------------------------------------------------------
# BehaviorEngine + servo de cámara
# ---------------------------------------------------------------------------
behavior  = BehaviorEngine(arduino=arduino, eyes=arduino.eyes)
cam_servo = CameraServoController(arduino._port, verbose=False)
cam_servo.center()

# Chime y estado visual de arranque
arduino.buzzer.startup_chime()
arduino.leds.on()
arduino.eyes.on()   # wake up GC9A01 displays (sleep-out + display-on)

# ---------------------------------------------------------------------------
# Tira de LEDs NeoPixel/WS2812
# Protocolo: LED:LED_1:COLOR:r,g,b  y  LED:LED_2:COLOR:r,g,b
# ---------------------------------------------------------------------------
_last_led_rgb: tuple = (-1, -1, -1)   # dedup — evita inundar el serial

def set_led_strip(r: int, g: int, b: int) -> None:
    """Establece el color terapéutico de los LEDs según la emoción (deduplicado)."""
    global _last_led_rgb
    if (r, g, b) == _last_led_rgb:
        return
    _last_led_rgb = (r, g, b)
    arduino.leds.set_color(r, g, b)

# ---------------------------------------------------------------------------
# Cámara CSI Jetson via GStreamer
# ---------------------------------------------------------------------------
GST_PIPELINE = (
    "nvarguscamerasrc sensor_id=0 ! "
    "video/x-raw(memory:NVMM),width=1280,height=720,framerate=60/1,format=NV12 ! "
    "nvvidconv flip-method=0 ! video/x-raw,width=640,height=480,format=BGRx ! "
    "videoconvert ! video/x-raw,format=BGR ! appsink drop=1 max-buffers=1 sync=false"
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
current_conf    = 0.0
_prev_had_face  = False   # para detectar transición no-cara → cara

print("Grabando... Pulsa Ctrl+C para detener.")
_has_display = False
try:
    cv2.namedWindow("Emotion Detection", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Emotion Detection", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    _has_display = True
except Exception:
    print("[Display] Sin pantalla — modo headless (solo grabación).")


# ---------------------------------------------------------------------------
# Lógica de movimiento del robot
# ---------------------------------------------------------------------------
def drive_toward_face(face_cx: int, emotion: str) -> None:
    """
    Mueve el robot hacia la cara detectada coordinando servo y tanque.

    Estrategia de dos niveles:
      · Servo NO en límite → servo corrige la orientación; tanque solo avanza.
      · Servo EN límite    → tanque gira para realinear el cuerpo (servo agotado).

    Respeta motor_pause del BEHAVIOR (emociones negativas → quieto = presencia).
    """
    if behavior.motor_should_pause(emotion):
        arduino.tank.stop()
        return

    # Si el servo puede corregir la orientación, el tanque solo avanza
    if not cam_servo.at_pan_limit:
        if arduino.can_move_forward:
            arduino.tank.forward(FWD_SPEED)
        else:
            arduino.tank.stop()
        return

    # Servo en su límite mecánico → tanque gira para realinear el cuerpo
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

        # FPS cada 30 frames
        if frame_count % 30 == 0:
            fps = 30 / (time() - fps_time)
            fps_time = time()

        # Detección de caras cada N frames
        if frame_count % DETECT_EVERY_N_FRAMES == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes, det_probs = detector.detect(rgb)

        # ── Procesar todas las caras detectadas ────────────────────────────
        faces_info = []

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

                face_cx  = (x1 + x2) // 2
                face_cy  = (y1 + y2) // 2
                face_roi = frame[y1:y2, x1:x2]
                emotion, emo_conf = classify_emotion(face_roi)

                faces_info.append({
                    "emotion":    emotion,
                    "confidence": float(emo_conf),
                    "cx":         face_cx,
                    "cy":         face_cy,
                })

                # Overlay visual (una caja por cara detectada)
                colors    = emotionMapper.get_color_dict(emotion, confidence=emo_conf)
                box_color = colors["dominant_rgb"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(frame, f"{emotion} {emo_conf:.0%}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, box_color, 2)

        face_count = len(faces_info)

        if face_count > 0:
            # ── Emoción de grupo: dominante ponderada por confianza ────────
            emo_scores = Counter()
            for f in faces_info:
                emo_scores[f["emotion"]] += f["confidence"]

            group_emotion, group_score = emo_scores.most_common(1)[0]
            total_score  = sum(emo_scores.values()) or 1.0
            group_conf   = float(group_score / total_score)

            # Cara primaria: la de mayor confianza (mirada y servo)
            primary = max(faces_info, key=lambda f: f["confidence"])

            current_emotion = group_emotion
            current_conf    = group_conf

            # Sonido de bienvenida al detectar la primera cara
            if not _prev_had_face:
                arduino.buzzer.beep(520, 80)   # Do (C5) suave — "te veo"
            _prev_had_face = True

            # Comportamiento médico (ojos cada frame; LEDs/buzzer al cambiar)
            changed = behavior.apply(
                group_emotion, group_conf,
                face_cx=primary["cx"],
                face_cy=primary["cy"],
                frame_w=FRAME_W,
                frame_h=FRAME_H,
            )

            if changed:
                r, g, b = behavior.get_led_strip_color(group_emotion)
                set_led_strip(r, g, b)
                b_cfg = BEHAVIOR.get(group_emotion, BEHAVIOR["neutral"])
                tag   = b_cfg.get("log_tag", group_emotion)
                print(f"[Behavior] {tag:10s} | faces={face_count} "
                      f"conf={group_conf:.0%} | strip=RGB({r},{g},{b})")

            # Servo de cámara — sigue la cara de mayor confianza
            cam_servo.track(primary["cx"], primary["cy"], FRAME_W, FRAME_H)

            # Movimiento del robot (respeta motor_pause del BEHAVIOR)
            drive_toward_face(primary["cx"], group_emotion)

        else:
            # Sin cara: modo espera
            _prev_had_face  = False
            current_emotion = "no_face"
            current_conf    = 0.0
            arduino.tank.stop()
            cam_servo.update_idle()
            behavior.apply("no_face")
            r, g, b = behavior.get_led_strip_color("no_face")
            set_led_strip(r, g, b)

        # HUD — información en el frame grabado
        us_cm = arduino.ultrasonic.distance_cm
        us_str = f"{us_cm:.0f}cm" if us_cm >= 0 else "--"
        hud_text = (f"FPS:{fps:.0f}  Faces:{face_count}  "
                    f"US:{us_str}  {current_emotion} {current_conf:.0%}")
        cv2.putText(frame, hud_text,
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        out.write(frame)

        if _has_display:
            try:
                cv2.imshow("Emotion Detection", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            except Exception:
                pass   # display perdido — ignorar

except KeyboardInterrupt:
    print("\nDetenido por el usuario.")

finally:
    cam_servo.close()
    arduino.stop()
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Vídeo guardado en {OUTPUT_PATH}")
