import cv2
import numpy as np
import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit
from facenet_pytorch import MTCNN
import torch
from time import time

#  Config 
FRAME_W, FRAME_H = 640, 480
CONF_THRESHOLD = 0.90
DETECT_EVERY_N_FRAMES = 2
OUTPUT_PATH = "/home/jetson/prueba/output.mp4"
EMOTIONS = ["neutral", "happiness", "surprise", "sadness",
            "anger", "disgust", "fear", "contempt"]
COLOR_MAP = {
    "happiness": (0, 255, 0),   "anger":    (0, 0, 255),
    "sadness":   (255, 0, 0),   "surprise": (0, 255, 255),
    "fear":      (128, 0, 128), "disgust":  (0, 128, 0),
    "contempt":  (128, 128, 0), "neutral":  (200, 200, 200),
}

#  TensorRT engine 
TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
runtime = trt.Runtime(TRT_LOGGER)

with open("/home/jetson/prueba/emotion.trt", "rb") as f:
    engine = runtime.deserialize_cuda_engine(f.read())

context = engine.create_execution_context()

input_shape  = (1, 1, 64, 64)
output_shape = (1, 8)
dtype = np.float32

h_input  = cuda.pagelocked_empty(trt.volume(input_shape),  dtype=dtype)
h_output = cuda.pagelocked_empty(trt.volume(output_shape), dtype=dtype)
d_input  = cuda.mem_alloc(h_input.nbytes)
d_output = cuda.mem_alloc(h_output.nbytes)
stream   = cuda.Stream()

context.set_tensor_address("Input3",           int(d_input))
context.set_tensor_address("Plus692_Output_0", int(d_output))

def classify_emotion(face_roi: np.ndarray) -> tuple[str, float]:
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

#  MTCNN 
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"MTCNN device: {device}")

mtcnn = MTCNN(
    keep_all=True, device=device,
    min_face_size=60,
    thresholds=[0.7, 0.8, 0.9],
    post_process=False,
    select_largest=False,
)

#  Cámara 
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

#  Estado 
boxes       = None
det_probs   = None
frame_count = 0
fps_time    = time()
fps         = 0.0

print("Grabando... Pulsa Ctrl+C para detener.")

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
                color = COLOR_MAP.get(emotion, (255, 255, 255))

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{emotion} {emo_conf:.0%}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.55, color, 2)
                if face_count == 1:
                    face_center = [x2 - x1, y2 - y1]
                    print(f"Emotion: {emotion} at {face_center}")

        cv2.putText(frame, f"FPS: {fps:.1f} | Faces: {face_count}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        out.write(frame)

        try:
            cv2.imshow("Emotion Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        except Exception:
            pass  # SSH sin display, ignorar

except KeyboardInterrupt:
    print("\nDetenido por el usuario.")

finally:
    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Vídeo guardado en {OUTPUT_PATH}")