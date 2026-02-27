# Emotion Detection — Jetson Orin Nano

Pipeline completo de detección de emociones en tiempo real usando cámara CSI, MTCNN para detección facial y un modelo de clasificación de emociones optimizado con TensorRT.

---

## Arquitectura general

```
Cámara CSI (GStreamer)
        │
        ▼
  Frame BGR (640×480)
        │
        ├──[cada 2 frames]──▶ MTCNN (GPU) ──▶ bounding boxes + probabilidades
        │
        └──[cada frame]──────▶ por cada cara detectada:
                                    │
                                    ▼
                              Recorte ROI → escala de grises → resize 64×64
                                    │
                                    ▼
                            TensorRT Engine (emotion.trt)
                                    │
                                    ▼
                            Softmax → emoción + confianza
                                    │
                                    ▼
                          Anotación sobre frame → VideoWriter
```

---

## Componentes

### 1. Captura de vídeo — GStreamer + CSI

```python
GST_PIPELINE = (
    "nvarguscamerasrc sensor_id=0 ! "
    "video/x-raw(memory:NVMM),width=640,height=480,framerate=30/1,format=NV12 ! "
    "nvvidconv flip-method=0 ! video/x-raw,format=BGRx ! "
    "videoconvert ! video/x-raw,format=BGR ! appsink drop=1 max-buffers=1"
)
cap = cv2.VideoCapture(GST_PIPELINE, cv2.CAP_GSTREAMER)
```

`nvarguscamerasrc` es el source nativo de NVIDIA para cámara CSI. El frame viaja siempre en memoria NVMM (memoria del acelerador multimedia de la Jetson) hasta `nvvidconv`, que lo convierte a BGRx en CPU-visible. `drop=1 max-buffers=1` en el appsink descarta frames si el procesamiento va lento, garantizando latencia mínima a costa de no procesar todos los frames.

---

### 2. Detección facial — MTCNN

```python
mtcnn = MTCNN(
    keep_all=True, device=device,
    min_face_size=60,
    thresholds=[0.7, 0.8, 0.9],
    post_process=False,
    select_largest=False,
)
```

MTCNN (Multi-task Cascaded Convolutional Networks) es una red en tres etapas (P-Net → R-Net → O-Net) que combina detección y alineamiento facial.

- `keep_all=True` — devuelve todas las caras detectadas, no solo la más grande.
- `min_face_size=60` — descarta caras de menos de 60px, reduce falsos positivos a distancia.
- `thresholds=[0.7, 0.8, 0.9]` — umbral de confianza por etapa (P-Net, R-Net, O-Net). La última etapa es la más restrictiva.
- `post_process=False` — devuelve píxeles en rango [0, 255] en lugar de normalizado, necesario porque usamos el ROI directamente de OpenCV.
- `select_largest=False` — no filtra por tamaño, detecta todas.

**Qué devuelve `mtcnn.detect(rgb)`:**
- `boxes` — array `(N, 4)` con coordenadas `[x1, y1, x2, y2]` de cada cara.
- `det_probs` — array `(N,)` con la probabilidad de cara para cada bounding box.

Se ejecuta **cada 2 frames** (`DETECT_EVERY_N_FRAMES = 2`) para no saturar la GPU, reutilizando los boxes del frame anterior en los frames intermedios.

---

### 3. Modelo de emociones — TensorRT Engine

#### Modelo original
El engine `.trt` proviene del modelo **FER+ (Facial Expression Recognition Plus)** de Microsoft, publicado en ONNX Model Zoo. Es una CNN ligera entrenada sobre el dataset FER+, que extiende FER2013 con etiquetas multi-evaluador para reducir el ruido de anotación.

Arquitectura: red convolucional de ~5 capas con BatchNorm.  
Input: imagen en escala de grises `(1, 1, 64, 64)` — batch=1, canales=1, 64×64 píxeles.  
Output: 8 logits sin activación final `(1, 8)`.

#### Las 8 clases (en orden de índice)
| Índice | Emoción   |
|--------|-----------|
| 0      | neutral   |
| 1      | happiness |
| 2      | surprise  |
| 3      | sadness   |
| 4      | anger     |
| 5      | disgust   |
| 6      | fear      |
| 7      | contempt  |

#### Conversión y ejecución con TensorRT

```python
with open("/home/jetson/prueba/emotion.trt", "rb") as f:
    engine = runtime.deserialize_cuda_engine(f.read())
context = engine.create_execution_context()
```

El engine ya está compilado para la GPU de la Jetson Orin Nano (Ampere). Se deserializa una vez al arrancar y se reutiliza en cada inferencia.

Los buffers de memoria se crean como **page-locked (pinned memory)** para maximizar el throughput en las transferencias CPU↔GPU:

```python
h_input  = cuda.pagelocked_empty(trt.volume(input_shape),  dtype=np.float32)
h_output = cuda.pagelocked_empty(trt.volume(output_shape), dtype=np.float32)
d_input  = cuda.mem_alloc(h_input.nbytes)
d_output = cuda.mem_alloc(h_output.nbytes)
stream   = cuda.Stream()
```

Los tensores se registran por nombre (nombres del grafo ONNX original):

```python
context.set_tensor_address("Input3",           int(d_input))
context.set_tensor_address("Plus692_Output_0", int(d_output))
```

#### Función de inferencia

```python
def classify_emotion(face_roi: np.ndarray) -> tuple[str, float]:
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
```

El preprocesado es intencionalmente mínimo: solo escala de grises + resize a 64×64 + cast a float32. No hay normalización explícita porque el modelo FER+ fue entrenado con píxeles en [0, 255].

La softmax se aplica manualmente con el truco de estabilidad numérica `logits - logits.max()` para evitar overflow en `exp`.

---

### 4. Loop principal

```python
if frame_count % DETECT_EVERY_N_FRAMES == 0:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    boxes, det_probs = mtcnn.detect(rgb)
```

MTCNN espera RGB, OpenCV entrega BGR — la conversión es obligatoria aquí.

```python
if det_probs[i] < CONF_THRESHOLD:  # 0.90
    continue
```

Umbral alto (90%) para filtrar detecciones dudosas antes de llamar al clasificador.

```python
if frame_count % 30 == 0:
    fps = 30 / (time() - fps_time)
    fps_time = time()
```

El FPS se recalcula cada 30 frames para no añadir overhead de `time()` en cada iteración.

---

### 5. Salida

- **VideoWriter** escribe el vídeo anotado en `/home/jetson/prueba/output.mp4` a 15 fps con codec `mp4v`.
- `cv2.imshow` está envuelto en `try/except` para no crashear cuando se ejecuta por SSH sin display.

---

## Dependencias clave

| Librería | Rol |
|---|---|
| `tensorrt` | Runtime de inferencia optimizada |
| `pycuda` | Interfaz Python para CUDA (buffers, streams, memcpy) |
| `facenet_pytorch` | MTCNN para detección facial |
| `torch` | Backend GPU para MTCNN |
| `opencv` | Captura GStreamer, preprocesado, anotación, escritura de vídeo |
| `numpy` | Buffers de transferencia y softmax manual |