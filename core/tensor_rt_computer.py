import cv2
import numpy as np
import onnxruntime as ort
from facenet_pytorch import MTCNN
import torch
from time import time

from processing.emotion_color_mapper import EmotionColorMapper

# Config
FRAME_W, FRAME_H = 640, 480
CONF_THRESHOLD = 0.90
DETECT_EVERY_N_FRAMES = 2
OUTPUT_PATH = "output.mp4"
EMOTIONS = ["neutral", "happiness", "surprise", "sadness",
            "anger", "disgust", "fear", "contempt"]

# ONNX Runtime — CoreML en Apple Silicon, CPU como fallback
providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
session = ort.InferenceSession("core/emotion.onnx", providers=providers)
input_name  = session.get_inputs()[0].name   # "Input3"
output_name = session.get_outputs()[0].name  # "Plus692_Output_0"

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

# MTCNN — CPU para compatibilidad
device = torch.device("cpu")
print(f"MTCNN device: {device}")

mtcnn = MTCNN(
    keep_all=True, device=device,
    min_face_size=60,
    thresholds=[0.7, 0.8, 0.9],
    post_process=False,
    select_largest=False,
)

# Emmotion mapper
emotionMapper = EmotionColorMapper()

# Cámara — webcam estándar (0 = built-in, 1 = externa)
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
if not cap.isOpened():
    raise RuntimeError("No se pudo abrir la cámara.")

out = cv2.VideoWriter(OUTPUT_PATH, cv2.VideoWriter_fourcc(*"mp4v"),
                      15, (FRAME_W, FRAME_H))

boxes       = None
det_probs   = None
frame_count = 0
fps_time    = time()
fps         = 0.0

print("Grabando... Pulsa 'q' para detener.")

# Pantalla completa
cv2.namedWindow("Emotion Detection", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Emotion Detection", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

try:
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("No frame received.")
            break

        frame_count += 1

        if frame_count % 120 == 0:
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
                colors = emotionMapper.get_color_dict(emotion, confidence=emo_conf)

                box_color = colors['dominant_rgb']
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                cv2.putText(frame, f"{emotion} {emo_conf:.0%}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, box_color, 2)
                if face_count == 1:
                    face_center = [x2 - x1, y2 - y1]
                    print(f"Emotion: {emotion} at {face_center}")
                    print(box_color)

        cv2.putText(frame, f"FPS: {fps:.1f} | Faces: {face_count}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        out.write(frame)
        cv2.imshow("Emotion Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print("\nDetenido.")

finally:
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Vídeo guardado en {OUTPUT_PATH}")