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