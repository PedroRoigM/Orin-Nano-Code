"""
tensor_rt_computer.py
=====================
Pipeline PC — ojos en pantalla + cuello servo.

· MTCNN detecta caras
· ONNX clasifica emoción → anima los ojos (RoboticEyeRenderer)
· CameraServoController mueve el cuello para seguir la primera cara

Ventana:
  ┌─────────────────────┬─────────────┐
  │  Cámara  640×480    │  OJO IZQ    │
  │                     │  240×240    │
  │                     ├─────────────┤
  │                     │  OJO DER    │
  │                     │  240×240    │
  └─────────────────────┴─────────────┘

Ejecutar:
    cd core && .venv/bin/python3 tensor_rt_computer.py [--camera N]
"""

import sys
import argparse
import time as _time
import cv2
import numpy as np
import onnxruntime as ort
import torch
from facenet_pytorch import MTCNN
from time import time

sys.path.insert(0, ".")
from GUI.visual_eyes                      import RoboticEyeRenderer
from controllers.camera_servo_controller  import CameraServoController

# ─────────────────────────────────────────────────────────────────────────────
# Argumentos
# ─────────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Robot médico — ojos + cuello")
parser.add_argument("--camera", type=int, default=0,
                    help="Índice de la cámara (0=built-in, 1=externa)")
args = parser.parse_args()

# ─────────────────────────────────────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────────────────────────────────────
FRAME_W, FRAME_H      = 640, 480
CONF_THRESHOLD        = 0.70
DETECT_EVERY_N_FRAMES = 2
EYE_SIZE              = 240

EMOTIONS = ["neutral", "happiness", "surprise", "sadness",
            "anger",   "disgust",   "fear",     "contempt"]

# Puerto del Arduino de cuello (Demo_neck.ino).
# None = sin hardware, solo visual.
NECK_PORT = '/dev/cu.usbmodem1101'   # ej. 'COM5' en Windows
NECK_BAUD = 9600

# ─────────────────────────────────────────────────────────────────────────────
# ONNX — clasificación de emoción (CoreML en Apple Silicon, CPU como fallback)
# ─────────────────────────────────────────────────────────────────────────────
_providers  = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
_session    = ort.InferenceSession("core/emotion.onnx", providers=_providers)
_in_name    = _session.get_inputs()[0].name
_out_name   = _session.get_outputs()[0].name


def classify_emotion(face_roi: np.ndarray) -> tuple[str, float]:
    if face_roi.size == 0:
        return "neutral", 0.0
    gray    = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (64, 64)).astype(np.float32)
    logits  = _session.run([_out_name], {_in_name: resized.reshape(1, 1, 64, 64)})[0].flatten()
    exp     = np.exp(logits - logits.max())
    probs   = exp / exp.sum()
    idx     = int(np.argmax(probs))
    return EMOTIONS[idx], float(probs[idx])


# ─────────────────────────────────────────────────────────────────────────────
# MTCNN — detección de caras
# ─────────────────────────────────────────────────────────────────────────────
mtcnn = MTCNN(
    keep_all=True, device=torch.device("cpu"),
    min_face_size=60, thresholds=[0.7, 0.8, 0.9],
    post_process=False, select_largest=False,
)

# ─────────────────────────────────────────────────────────────────────────────
# Puerto serial para el Arduino de cuello (Demo_neck.ino)
# Traduce: NECK:NECK_1:MOVE:<pan>,<tilt>  →  NECK:SRV_1:<pan>,<tilt>
# ─────────────────────────────────────────────────────────────────────────────
class _NeckPort:
    # CameraServoController envía: NECK:NECK_1:MOVE:<pan>,<tilt>
    # Demo_neck.ino espera       : NECK:SRV_1:<pan>,<tilt>
    _PREFIX_IN  = "NECK:NECK_1:MOVE:"
    _PREFIX_OUT = "NECK:SRV_1:"

    def __init__(self, port: str, baud: int = 9600) -> None:
        try:
            import serial
            self._ser = serial.Serial(port, baud, timeout=1)
            print(f"[NeckPort] Abierto {port} @ {baud} — esperando boot Arduino (2 s)…")
            _time.sleep(2.0)
            self._ser.reset_input_buffer()
            print("[NeckPort] Listo.")
        except Exception as e:
            print(f"[NeckPort] No disponible ({e}) — cuello desactivado.")
            self._ser = None

    def send_line(self, line: str) -> None:
        if self._ser is None or not self._ser.is_open:
            return
        if line.startswith(self._PREFIX_IN):
            line = f"{self._PREFIX_OUT}{line[len(self._PREFIX_IN):]}"
        try:
            self._ser.write((line + "\n").encode())
        except Exception as e:
            print(f"[NeckPort] ERROR: {e}")

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()


# ─────────────────────────────────────────────────────────────────────────────
# Hardware
# ─────────────────────────────────────────────────────────────────────────────
class _SilentPort:
    """Puerto nulo — descarta todos los comandos cuando NECK_PORT = None."""
    def send_line(self, line: str) -> None:
        pass


_neck_port = _NeckPort(NECK_PORT, NECK_BAUD) if NECK_PORT else None
cam_servo  = CameraServoController(_neck_port if _neck_port else _SilentPort(), verbose=False)
cam_servo.center()

eye_renderer = RoboticEyeRenderer()

# ─────────────────────────────────────────────────────────────────────────────
# Cámara
# ─────────────────────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(args.camera)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
if not cap.isOpened():
    raise RuntimeError("No se pudo abrir la cámara.")

# ─────────────────────────────────────────────────────────────────────────────
# Ventana — cámara a la izquierda, dos ojos a la derecha
# ─────────────────────────────────────────────────────────────────────────────
WIN_W   = FRAME_W + 10 + EYE_SIZE   # 890
WIN_H   = FRAME_H                    # 480
EYE_X   = FRAME_W + 10
EYE_L_Y = 0
EYE_R_Y = FRAME_H // 2

cv2.namedWindow("Robot Medico", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Robot Medico", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


def _draw_bezel(canvas: np.ndarray, x: int, y: int) -> None:
    cx, cy, r = x + EYE_SIZE // 2, y + EYE_SIZE // 2, EYE_SIZE // 2
    cv2.circle(canvas, (cx, cy), r + 6, (40, 40, 40), -1)
    cv2.circle(canvas, (cx, cy), r + 2, (18, 14, 16), -1)


def _paste_eye(canvas: np.ndarray, eye: np.ndarray, x: int, y: int) -> None:
    mask = np.zeros((EYE_SIZE, EYE_SIZE), dtype=np.uint8)
    cv2.circle(mask, (EYE_SIZE // 2, EYE_SIZE // 2), EYE_SIZE // 2, 255, -1)
    np.copyto(canvas[y:y + EYE_SIZE, x:x + EYE_SIZE],
              eye, where=(mask > 0)[:, :, None])


# ─────────────────────────────────────────────────────────────────────────────
# Estado
# ─────────────────────────────────────────────────────────────────────────────
boxes       = None
det_probs   = None
frame_count = 0
fps_time    = time()
fps         = 0.0

print("Pulsa 'q' para salir.")

# ─────────────────────────────────────────────────────────────────────────────
# Bucle principal
# ─────────────────────────────────────────────────────────────────────────────
try:
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        frame_count += 1

        if frame_count % 120 == 0:
            fps = 120 / (time() - fps_time)
            fps_time = time()

        if frame_count % DETECT_EVERY_N_FRAMES == 0:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes, det_probs = mtcnn.detect(rgb)

        face_found = False

        if boxes is not None:
            for i, box in enumerate(boxes):
                if det_probs[i] < CONF_THRESHOLD:
                    continue
                x1 = max(0, int(box[0]));  y1 = max(0, int(box[1]))
                x2 = min(FRAME_W, int(box[2])); y2 = min(FRAME_H, int(box[3]))
                if x2 <= x1 or y2 <= y1:
                    continue

                face_cx  = (x1 + x2) // 2
                face_cy  = (y1 + y2) // 2
                emotion, conf = classify_emotion(frame[y1:y2, x1:x2])

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 0), 2)
                cv2.putText(frame, f"{emotion} {conf:.0%}",
                            (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 1)

                if not face_found:   # primera cara → servo + ojos
                    gaze_x = (face_cx - FRAME_W / 2) / (FRAME_W / 2)
                    gaze_y = (face_cy - FRAME_H / 2) / (FRAME_H / 2)
                    eye_renderer.update(gaze_x, gaze_y, emotion)
                    cam_servo.track(face_cx, face_cy, FRAME_W, FRAME_H)
                    face_found = True

        if not face_found:
            eye_renderer.set_idle()
            cam_servo.update_idle()

        # ── Componer ventana ─────────────────────────────────────────────────
        canvas = np.zeros((WIN_H, WIN_W, 3), dtype=np.uint8)
        canvas[:FRAME_H, :FRAME_W] = frame
        canvas[:, FRAME_W:FRAME_W + 10] = (25, 25, 25)

        eye_l, eye_r = eye_renderer.get_frames()
        _draw_bezel(canvas, EYE_X, EYE_L_Y)
        _draw_bezel(canvas, EYE_X, EYE_R_Y)
        _paste_eye(canvas, eye_l, EYE_X, EYE_L_Y)
        _paste_eye(canvas, eye_r, EYE_X, EYE_R_Y)

        cv2.putText(canvas, f"FPS:{fps:.0f}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow("Robot Medico", canvas)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print("\nDetenido.")

finally:
    cam_servo.close()
    if _neck_port:
        _neck_port.close()
    cap.release()
    cv2.destroyAllWindows()
