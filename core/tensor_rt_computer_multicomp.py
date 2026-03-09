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
from collections import Counter
import cv2
import numpy as np
import onnxruntime as ort
from facenet_pytorch import MTCNN
import torch
from time import time

from processing.emotion_color_mapper      import EmotionColorMapper
from controllers.eyes_controller          import EyesController
from companion_behavior                   import BehaviorEngine, BEHAVIOR
from GUI.visual_eyes                      import RobotWindow

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
CONF_THRESHOLD        = 0.70
DETECT_EVERY_N_FRAMES = 2
OUTPUT_PATH           = "output.mp4"

EMOTIONS = ["neutral", "happiness", "surprise", "sadness",
            "anger",   "disgust",   "fear",     "contempt"]

ARDUINO_PORT         = 'COM13'              # None = auto-detectar; o forzar: "/dev/cu.usbmodemXXXX"
ARDUINO_BAUD         = 115200
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
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Detección automática del puerto Arduino
# ---------------------------------------------------------------------------
def _detect_arduino_port() -> str | None:
    """Devuelve el puerto del Arduino o None si no se encuentra."""
    if ARDUINO_PORT is not None:
        return ARDUINO_PORT
    try:
        import serial.tools.list_ports
        candidates = []
        for p in serial.tools.list_ports.comports():
            dev = p.device or ""
            desc = (p.description or "").lower()
            if ("arduino" in desc or "mega" in desc
                    or "usbmodem" in dev or "ttyACM" in dev or "usbserial" in dev):
                candidates.append(dev)
        if candidates:
            port = candidates[0]
            print(f"[Arduino] Puerto auto-detectado: {port}")
            return port
    except Exception:
        pass
    return None

# Arduino — real si está disponible, MockArduino en caso contrario
# ---------------------------------------------------------------------------
arduino = None
from controllers.arduino_controller import ArduinoController

_port = _detect_arduino_port() or "MOCK"
arduino = ArduinoController(_port, ARDUINO_BAUD, ULTRASONIC_THRESHOLD)

def _on_obstacle(cm: float) -> None:
    arduino.tank.stop()
    arduino.leds.blink()
    # react_to_obstacle ya se llama internamente en ArduinoController vía EmotionManager
    print(f"[Obstacle] {cm:.1f} cm — motor detenido")

arduino.on_obstacle = _on_obstacle
arduino.start()

if _port != "MOCK":
    arduino.buzzer.startup_chime()
    arduino.leds.on()
    print("[Arduino] Hardware conectado en", _port)
else:
    print("[Arduino] Usando modo MOCK — comandos seriales visibles en terminal.\n")


# ---------------------------------------------------------------------------
# SimulatedEyes — EyeRenderer con interfaz compatible con GC9A01Controller
# ---------------------------------------------------------------------------
# El renderizador visual ha sido movido a GUI.visual_eyes
# ---------------------------------------------------------------------------
# Inicializar ojos y BehaviorEngine
# ---------------------------------------------------------------------------
# visual_eyes: renderizador visual en pantalla (puro OpenCV, sin serial)
# arduino.eyes: EyesController / MockEyes → gestiona los comandos SERIAL →
# BehaviorEngine usa arduino.eyes (no visual_eyes) para el comportamiento médico.
robot_window = RobotWindow(FRAME_W, FRAME_H, EYE_DISPLAY_SIZE)
visual_eyes  = robot_window.robot_eyes
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
# La gestión de la ventana ha sido abstraída a RobotWindow (GUI/visual_eyes.py)

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

                face_cx = (x1 + x2) // 2
                face_cy = (y1 + y2) // 2
                face_roi = frame[y1:y2, x1:x2]
                emotion, emo_conf = classify_emotion(face_roi)

                faces_info.append(
                    {
                        "emotion":    emotion,
                        "confidence": float(emo_conf),
                        "cx":         face_cx,
                        "cy":         face_cy,
                    }
                )

                # Overlay visual en el frame (una caja por cara)
                colors    = emotionMapper.get_color_dict(emotion, confidence=emo_conf)
                box_color = colors["dominant_rgb"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(frame, f"{emotion} {emo_conf:.0%}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, box_color, 2)

        face_count = len(faces_info)

        if face_count > 0:
            # Agregación de grupo: emoción dominante ponderada por confianza
            emo_scores = Counter()
            for f in faces_info:
                emo_scores[f["emotion"]] += f["confidence"]

            group_emotion, group_score = emo_scores.most_common(1)[0]
            total_score = sum(emo_scores.values()) or 1.0
            group_conf  = float(group_score / total_score)

            # Cara principal: la de mayor confianza (usada para mirada)
            primary = max(faces_info, key=lambda f: f["confidence"])

            current_emotion = group_emotion
            current_conf    = group_conf

            changed = behavior.apply(
                group_emotion,
                group_conf,
                face_cx=primary["cx"],
                face_cy=primary["cy"],
                frame_w=FRAME_W,
                frame_h=FRAME_H,
            )

            if changed:
                r, g, b = behavior.get_led_strip_color(group_emotion)
                set_led_strip(r, g, b)
                b_cfg = BEHAVIOR.get(group_emotion, BEHAVIOR.get("neutral", {}))
                tag   = b_cfg.get("log_tag", group_emotion)
                led   = b_cfg.get("led", "OFF")
                buz   = b_cfg.get("buzzer")
                lcd1  = b_cfg.get("lcd_line1", "")
                lcd2  = b_cfg.get("lcd_line2", "")
                print(
                    f"[Behavior→Arduino] faces={face_count} "
                    f"group={tag:10s} conf={group_conf:.0%} "
                    f"LED={led} strip=RGB({r},{g},{b}) "
                    f"buzzer={buz} lcd=({lcd1!r}, {lcd2!r})"
                )

            # Actualizar renderizador visual (SimulatedEyes, pantalla local)
            gaze_x_v = (primary["cx"] - FRAME_W / 2) / (FRAME_W / 2)
            gaze_y_v = (primary["cy"] - FRAME_H / 2) / (FRAME_H / 2)
            visual_eyes.update(gaze_x_v, gaze_y_v, group_emotion)

        if frame_count % 30 == 0:
            n_raw = len(boxes) if boxes is not None else 0
            print(f"[Det] frame={frame_count} raw={n_raw} passed={face_count} "
                  f"emotion={current_emotion} conf={current_conf:.0%}")

        if face_count == 0:
            # Sin cara detectada (boxes None o todas bajo el umbral)
            behavior.apply("no_face")
            visual_eyes.set_idle()
            r, g, b = behavior.get_led_strip_color("no_face")
            set_led_strip(r, g, b)
            current_emotion = "no_face"
            current_conf    = 0.0

        # ── Componer ventana final ────────────────────────────────────────────
        # MockSerial has is_mock, ArduinoController._ser does not
        if hasattr(arduino, '_ser') and hasattr(arduino._ser, 'is_mock'):
            hw_mode = "SIM" if arduino._ser.is_mock else "HW"
        else:
            hw_mode = "HW"
            
        us_val  = f"{arduino.ultrasonic.distance_cm:.0f}cm"
        b_info  = BEHAVIOR.get(current_emotion, BEHAVIOR["neutral"])
        tag_str = b_info.get("log_tag", current_emotion)
        led_str = b_info.get("led", "OFF")

        robot_window.update_and_show(
            camera_frame=frame,
            fps=fps,
            face_count=face_count,
            group_emotion=current_emotion,
            group_conf=current_conf,
            hw_mode_str=hw_mode,
            us_distance_str=us_val,
            behavior_tag=tag_str,
            log_led=led_str
        )

        out.write(frame)

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