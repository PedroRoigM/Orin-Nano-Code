"""
gc9a01_tester.py
================
Simulador visual para el controlador de pantallas GC9A01 (ojos del robot R2).

Muestra en pantalla dos círculos de 240×240 px que simulan exactamente lo que
aparecerá en los displays físicos redondos: ojos animados con iris de color,
pupila que sigue la cara detectada por webcam, y parpadeos automáticos.

Modos de operación (detecta automáticamente lo que está disponible):
  · Full:    webcam + detección de caras (MTCNN) + clasificación emociones (ONNX)
  · Parcial: webcam visible, pero sin detección automática → usa el ratón
  · Demo:    sin webcam → animación automática con emociones cíclicas

Controles de teclado:
  1-8     → forzar emoción (neutral, happiness, surprise, sadness,
                             anger, disgust, fear, contempt)
  B       → parpadeo manual
  C       → activar / desactivar cámara
  M       → toggle: seguir ratón / seguir cara
  D       → modo demo (animación automática)
  Q / ESC → salir

Ejecución:
  cd core
  python gc9a01_tester.py

  # Con cámara específica:
  python gc9a01_tester.py --camera 1

  # Solo demo (sin cámara):
  python gc9a01_tester.py --demo
"""

import sys
import math
import time
import random
import argparse
import threading
from pathlib import Path
from typing import Optional

import numpy as np
import cv2

# ── Añadir core/ y core/controllers/ al path para imports relativos ───────────
_CORE_DIR = Path(__file__).parent
sys.path.insert(0, str(_CORE_DIR))
sys.path.insert(0, str(_CORE_DIR / "controllers"))

from gc9a01_controller import (
    EyeRenderer,
    IRIS_COLOR_RGB,
    EYE_PARAMS,
    BLINK_DURATION,
    LERP_GAZE,
    LERP_COLOR,
    MAX_GAZE_PX,
)

# ── Imports opcionales para detección ─────────────────────────────────────────
try:
    import torch
    from facenet_pytorch import MTCNN
    _MTCNN_OK = True
except ImportError:
    _MTCNN_OK = False

try:
    import onnxruntime as ort
    _ORT_OK = True
except ImportError:
    _ORT_OK = False

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de UI
# ─────────────────────────────────────────────────────────────────────────────
EMOTIONS = ["neutral", "happiness", "surprise", "sadness",
            "anger", "disgust", "fear", "contempt"]

# Colores BGR (OpenCV) para cada emoción — derivados de IRIS_COLOR_RGB
def _rgb_to_bgr(rgb: tuple) -> tuple:
    return (rgb[2], rgb[1], rgb[0])

IRIS_COLOR_BGR = {k: _rgb_to_bgr(v) for k, v in IRIS_COLOR_RGB.items()}

# Colores de la UI (BGR)
UI_BG           = (25, 18, 20)       # fondo general
UI_PANEL        = (35, 28, 32)       # fondo paneles
UI_ACCENT       = (80, 180, 255)     # azul claro
UI_TEXT         = (220, 218, 215)    # texto principal
UI_TEXT_DIM     = (120, 115, 110)    # texto secundario
UI_BEZEL        = (55, 50, 52)       # bisel de la pantalla
UI_BEZEL_INNER  = (18, 14, 16)       # interior del bisel

# Layout
WIN_W, WIN_H    = 1080, 580
LEFT_W          = 400               # ancho del panel izquierdo (cámara + info)
EYE_DISPLAY     = 256               # diámetro de cada ojo en el tester (px)
EYE_L_CX        = LEFT_W + (WIN_W - LEFT_W) // 4              # centro ojo izq
EYE_R_CX        = LEFT_W + 3 * (WIN_W - LEFT_W) // 4          # centro ojo der
EYE_CY          = WIN_H // 2 - 10

CAM_W, CAM_H    = 380, 285          # tamaño del feed de cámara en tester

FRAME_W, FRAME_H = 640, 480
ONNX_PATH = _CORE_DIR / "emotion.onnx"

EMOTION_LABELS_ES = {
    "neutral":   "Neutral",
    "happiness": "Alegría",
    "surprise":  "Sorpresa",
    "sadness":   "Tristeza",
    "anger":     "Enfado",
    "disgust":   "Asco",
    "fear":      "Miedo",
    "contempt":  "Desprecio",
}


# ─────────────────────────────────────────────────────────────────────────────
# GC9A01Tester
# ─────────────────────────────────────────────────────────────────────────────
class GC9A01Tester:
    """
    Simulador visual que replica exactamente lo que mostrarán las dos
    pantallas GC9A01 físicas.
    """

    def __init__(self, camera_index: int = 0, demo_mode: bool = False):
        # Estado de los ojos
        self._emotion       = "neutral"
        self._confidence    = 1.0
        self._gaze_x        = 0.0   # actual suavizado
        self._gaze_y        = 0.0
        self._tgt_gaze_x    = 0.0
        self._tgt_gaze_y    = 0.0
        self._iris_bgr      = list(IRIS_COLOR_BGR["neutral"])
        self._tgt_iris_bgr  = list(IRIS_COLOR_BGR["neutral"])
        self._blink_start   = None
        self._blink_factor  = 1.0
        self._next_blink    = time.time() + random.uniform(3.0, 7.0)

        # Control UI
        self._manual_emotion   = False   # True si el usuario fijó emoción con 1-8
        self._follow_mouse     = False
        self._demo_mode        = demo_mode
        self._cam_active       = not demo_mode
        self._show_cam         = True
        self._running          = True

        # Detección (hilo background)
        self._lock             = threading.Lock()
        self._last_cam_frame   = None   # frame de cámara para mostrar
        self._detected_face    = None   # (gaze_x, gaze_y) normalizado, o None
        self._detected_emotion = None
        self._detected_conf    = 0.0
        self._detection_active = False

        # Cámara
        self._cap    = None
        self._mtcnn  = None
        self._ort    = None
        self._ort_in = None
        self._ort_out = None

        if not demo_mode:
            self._init_camera(camera_index)
            self._init_models()

        # Renderer
        self._renderer = EyeRenderer()

        # Mouse (para debug sin cara)
        cv2.namedWindow("GC9A01 Eye Simulator", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("GC9A01 Eye Simulator", WIN_W, WIN_H)
        cv2.setMouseCallback("GC9A01 Eye Simulator", self._on_mouse)

    # ── Inicialización ────────────────────────────────────────────────────────

    def _init_camera(self, index: int) -> None:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
            self._cap = cap
            print(f"[Tester] Cámara {index} abierta.")
        else:
            print(f"[Tester] No se pudo abrir cámara {index} — modo sin cámara.")
            self._cam_active = False

    def _init_models(self) -> None:
        if _MTCNN_OK:
            try:
                device = "cpu"
                self._mtcnn = MTCNN(
                    keep_all=True, device=device,
                    min_face_size=50,
                    thresholds=[0.7, 0.8, 0.9],
                    post_process=False,
                )
                print("[Tester] MTCNN cargado (detección de caras).")
            except Exception as e:
                print(f"[Tester] MTCNN no disponible: {e}")

        if _ORT_OK and ONNX_PATH.exists():
            try:
                providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]
                self._ort     = ort.InferenceSession(str(ONNX_PATH), providers=providers)
                self._ort_in  = self._ort.get_inputs()[0].name
                self._ort_out = self._ort.get_outputs()[0].name
                print(f"[Tester] ONNX cargado ({ONNX_PATH.name}).")
            except Exception as e:
                print(f"[Tester] ONNX no disponible: {e}")

        # Arrancar hilo de detección si hay al menos cámara
        if self._cap and self._cap.isOpened():
            self._detection_active = True
            t = threading.Thread(target=self._detection_loop, daemon=True)
            t.start()

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_mouse(self, event, x, y, flags, param) -> None:
        if self._follow_mouse:
            # Convertir posición del ratón sobre el área de los ojos a gaze
            rx = (x - LEFT_W) / (WIN_W - LEFT_W) * 2.0 - 1.0
            ry = y / WIN_H * 2.0 - 1.0
            with self._lock:
                self._tgt_gaze_x = float(np.clip(rx, -1.0, 1.0))
                self._tgt_gaze_y = float(np.clip(ry, -1.0, 1.0))

    # ── Hilo de detección ─────────────────────────────────────────────────────

    def _detection_loop(self) -> None:
        """Lee cámara y ejecuta detección de cara + emoción en background."""
        frame_n = 0
        boxes_cache   = None
        probs_cache   = None
        DETECT_EVERY  = 3   # detectar cara cada N frames

        while self._running and self._detection_active:
            if not self._cap or not self._cap.isOpened():
                time.sleep(0.05)
                continue

            ret, frame = self._cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            frame_n += 1

            # Detección de caras (cada DETECT_EVERY frames)
            if frame_n % DETECT_EVERY == 0 and self._mtcnn:
                try:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    boxes_cache, probs_cache = self._mtcnn.detect(rgb)
                except Exception:
                    boxes_cache = probs_cache = None

            # Procesar primera cara válida
            gaze_x = gaze_y = None
            emotion = None
            conf    = 0.0

            if boxes_cache is not None:
                for i, box in enumerate(boxes_cache):
                    if probs_cache[i] < 0.85:
                        continue
                    x1 = max(0, int(box[0])); y1 = max(0, int(box[1]))
                    x2 = min(FRAME_W, int(box[2])); y2 = min(FRAME_H, int(box[3]))
                    if x2 <= x1 or y2 <= y1:
                        continue

                    face_cx = (x1 + x2) / 2
                    face_cy = (y1 + y2) / 2
                    gaze_x  = (face_cx - FRAME_W / 2) / (FRAME_W / 2)
                    gaze_y  = (face_cy - FRAME_H / 2) / (FRAME_H / 2)

                    # Clasificar emoción
                    if self._ort:
                        try:
                            roi = frame[y1:y2, x1:x2]
                            if roi.size > 0:
                                gray  = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                                inp   = cv2.resize(gray, (64, 64)).astype(np.float32)
                                inp   = inp.reshape(1, 1, 64, 64)
                                logit = self._ort.run([self._ort_out], {self._ort_in: inp})[0].flatten()
                                exp_l = np.exp(logit - logit.max())
                                probs = exp_l / exp_l.sum()
                                idx   = int(np.argmax(probs))
                                emotion = EMOTIONS[idx]
                                conf    = float(probs[idx])
                        except Exception:
                            pass

                    # Dibujar bounding box en frame
                    emo_label = emotion or "?"
                    box_color = IRIS_COLOR_BGR.get(emo_label, (0, 220, 100))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                    cv2.putText(frame, f"{emo_label} {conf:.0%}",
                                (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)
                    break  # solo la primera cara

            with self._lock:
                self._last_cam_frame = frame.copy()
                if gaze_x is not None:
                    self._detected_face    = (gaze_x, gaze_y)
                    self._detected_emotion = emotion
                    self._detected_conf    = conf
                else:
                    self._detected_face    = None

    # ── Lógica principal ──────────────────────────────────────────────────────

    def _update_state(self, now: float) -> None:
        """Actualiza gaze, color e iris suavizados cada frame."""
        # Fuente de la mirada
        with self._lock:
            face    = self._detected_face
            det_emo = self._detected_emotion
            det_con = self._detected_conf
            cam_frm = self._last_cam_frame

        if self._demo_mode:
            # Animación lissajous automática
            self._tgt_gaze_x = 0.72 * math.sin(now * 0.45)
            self._tgt_gaze_y = 0.40 * math.sin(now * 0.72 + 0.9)
            if not self._manual_emotion:
                idx = int(now / 4.5) % len(EMOTIONS)
                self._set_emotion(EMOTIONS[idx])
        elif self._follow_mouse:
            pass  # actualizado por _on_mouse
        elif face is not None and not self._follow_mouse:
            self._tgt_gaze_x, self._tgt_gaze_y = face
            if det_emo and not self._manual_emotion:
                self._set_emotion(det_emo, det_con)
        else:
            # Sin cara: mirada al centro, movimiento idle suave
            self._tgt_gaze_x = 0.15 * math.sin(now * 0.3)
            self._tgt_gaze_y = 0.10 * math.sin(now * 0.5)

        # Lerp gaze
        self._gaze_x += (self._tgt_gaze_x - self._gaze_x) * LERP_GAZE
        self._gaze_y += (self._tgt_gaze_y - self._gaze_y) * LERP_GAZE

        # Lerp color
        for i in range(3):
            self._iris_bgr[i] += (self._tgt_iris_bgr[i] - self._iris_bgr[i]) * LERP_COLOR

        # Parpadeo automático
        if self._blink_start is None and now >= self._next_blink:
            self._blink_start = now
            self._next_blink  = now + BLINK_DURATION + random.uniform(3.0, 8.0)

        # blink_factor
        bf = 1.0
        if self._blink_start is not None:
            elapsed = (now - self._blink_start) / BLINK_DURATION
            if   elapsed >= 1.0:  self._blink_start = None
            elif elapsed < 0.30:  bf = 1.0 - elapsed / 0.30
            elif elapsed < 0.40:  bf = 0.0
            else:                 bf = (elapsed - 0.40) / 0.60
        self._blink_factor = bf

        return cam_frm

    def _set_emotion(self, emotion: str, confidence: float = 1.0) -> None:
        if emotion in IRIS_COLOR_BGR:
            self._emotion    = emotion
            self._confidence = confidence
            self._tgt_iris_bgr = list(IRIS_COLOR_BGR[emotion])

    # ── Renderizado UI ────────────────────────────────────────────────────────

    def _render_eye_display(
        self, gaze_x: float, gaze_y: float, mirrored: bool
    ) -> np.ndarray:
        """Genera la imagen del ojo y la escala al tamaño de pantalla."""
        params = EYE_PARAMS.get(self._emotion, EYE_PARAMS["neutral"])
        eye240 = self._renderer.render(
            gaze_x, gaze_y,
            tuple(int(c) for c in self._iris_bgr),
            self._blink_factor,
            params["squint"],
            params["wide"],
            mirrored=mirrored,
            color_is_bgr=True,
        )
        return cv2.resize(eye240, (EYE_DISPLAY, EYE_DISPLAY), interpolation=cv2.INTER_LINEAR)

    def _draw_bezel(
        self, canvas: np.ndarray, eye_img: np.ndarray, cx: int, cy: int, label: str
    ) -> None:
        """Dibuja el bisel de la pantalla y pega el ojo en el canvas."""
        r   = EYE_DISPLAY // 2
        r_b = r + 8   # radio exterior del bisel

        # Bisel exterior (gradiente manual: 2 círculos)
        cv2.circle(canvas, (cx, cy), r_b + 4, (70, 65, 68), -1)
        cv2.circle(canvas, (cx, cy), r_b,     UI_BEZEL_INNER, -1)

        # Pegar ojo con máscara circular
        x0 = cx - r; y0 = cy - r
        x1 = cx + r; y1 = cy + r
        # Recortar si el ojo sale del canvas
        if x0 < 0 or y0 < 0 or x1 > WIN_W or y1 > WIN_H:
            return

        roi = canvas[y0:y1, x0:x1]
        mask = np.zeros((EYE_DISPLAY, EYE_DISPLAY), dtype=np.uint8)
        cv2.circle(mask, (r, r), r, 255, -1)
        roi[mask > 0] = eye_img[mask > 0]

        # Reflejo del bisel (arco superior brillante)
        cv2.ellipse(canvas, (cx, cy - 2), (r_b + 2, r_b + 2),
                    0, 200, 340, (95, 90, 92), 2, cv2.LINE_AA)

        # Etiqueta debajo
        txt_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0]
        tx = cx - txt_size[0] // 2
        ty = cy + r_b + 22
        cv2.putText(canvas, label, (tx, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, UI_TEXT_DIM, 1, cv2.LINE_AA)

    def _draw_left_panel(
        self, canvas: np.ndarray, cam_frame: Optional[np.ndarray], now: float
    ) -> None:
        """Panel izquierdo: cámara + info de emoción + controles."""
        # Fondo del panel
        cv2.rectangle(canvas, (0, 0), (LEFT_W, WIN_H), UI_PANEL, -1)
        cv2.line(canvas, (LEFT_W, 0), (LEFT_W, WIN_H), (50, 45, 48), 2)

        # Título
        cv2.putText(canvas, "GC9A01 Eye Simulator",
                    (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, UI_ACCENT, 1, cv2.LINE_AA)
        cv2.putText(canvas, "Robot R2 · Jetson Orin Nano",
                    (12, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.42, UI_TEXT_DIM, 1, cv2.LINE_AA)

        # Feed de cámara
        cam_y = 62
        if self._show_cam and cam_frame is not None:
            small = cv2.resize(cam_frame, (CAM_W, CAM_H))
            canvas[cam_y:cam_y + CAM_H, 10:10 + CAM_W] = small
            cv2.rectangle(canvas, (10, cam_y), (10 + CAM_W, cam_y + CAM_H), (60, 55, 58), 1)
        else:
            cv2.rectangle(canvas, (10, cam_y), (10 + CAM_W, cam_y + CAM_H), (40, 35, 38), -1)
            msg = "SIN CÁMARA" if not self._cam_active else "CÁMARA OFF"
            cv2.putText(canvas, msg,
                        (10 + CAM_W // 2 - 55, cam_y + CAM_H // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, UI_TEXT_DIM, 1, cv2.LINE_AA)

        # ── Emoción actual ──
        info_y = cam_y + CAM_H + 18
        emo_color = IRIS_COLOR_BGR.get(self._emotion, (200, 200, 200))
        emo_es    = EMOTION_LABELS_ES.get(self._emotion, self._emotion)

        # Círculo de color de emoción
        cv2.circle(canvas, (28, info_y + 10), 10, emo_color, -1, cv2.LINE_AA)
        cv2.putText(canvas, f"Emocion: {emo_es}",
                    (46, info_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.65, UI_TEXT, 1, cv2.LINE_AA)
        info_y += 32

        # Confianza
        bar_w = int(self._confidence * (LEFT_W - 46))
        cv2.rectangle(canvas, (46, info_y), (46 + bar_w, info_y + 8), emo_color, -1)
        cv2.rectangle(canvas, (46, info_y), (LEFT_W - 10, info_y + 8), UI_TEXT_DIM, 1)
        cv2.putText(canvas, f"{self._confidence:.0%}",
                    (12, info_y + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, UI_TEXT_DIM, 1)
        info_y += 22

        # Mirada
        cv2.putText(canvas, f"Mirada: X={self._gaze_x:+.2f}  Y={self._gaze_y:+.2f}",
                    (12, info_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.48, UI_TEXT_DIM, 1)
        info_y += 22

        # Parpadeo
        blink_txt = "Parpadeando" if self._blink_start is not None else "Abierto"
        cv2.putText(canvas, f"Parpado: {blink_txt}",
                    (12, info_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.48, UI_TEXT_DIM, 1)
        info_y += 30

        # Modo activo
        mode_parts = []
        if self._demo_mode:     mode_parts.append("DEMO")
        if self._follow_mouse:  mode_parts.append("RATON")
        if self._manual_emotion: mode_parts.append("MANUAL")
        if self._detection_active: mode_parts.append("DETECCION")
        mode_str = " | ".join(mode_parts) if mode_parts else "IDLE"
        cv2.putText(canvas, f"Modo: {mode_str}",
                    (12, info_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.48, UI_ACCENT, 1)
        info_y += 30

        # ── Controles ──
        controls = [
            "1-8  → emocion manual",
            "B    → parpadeo",
            "C    → camara on/off",
            "M    → seguir raton",
            "D    → modo demo",
            "Q/ESC → salir",
        ]
        for line in controls:
            cv2.putText(canvas, line,
                        (12, info_y + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.42, UI_TEXT_DIM, 1)
            info_y += 18

    def _draw_emotion_palette(self, canvas: np.ndarray) -> None:
        """Barra de paleta de emociones en la parte inferior derecha."""
        bar_x = LEFT_W + 10
        bar_y = WIN_H - 28
        dot_r = 9
        gap   = (WIN_W - LEFT_W - 20) // len(EMOTIONS)

        for i, emo in enumerate(EMOTIONS):
            cx_dot = bar_x + i * gap + gap // 2
            color  = IRIS_COLOR_BGR[emo]
            filled = (emo == self._emotion)
            cv2.circle(canvas, (cx_dot, bar_y), dot_r, color, -1 if filled else 1, cv2.LINE_AA)
            if filled:
                cv2.circle(canvas, (cx_dot, bar_y), dot_r + 3, color, 1, cv2.LINE_AA)
            cv2.putText(canvas, str(i + 1),
                        (cx_dot - 4, bar_y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                        UI_TEXT if filled else UI_TEXT_DIM, 1)

    def _compose_frame(self, cam_frame: Optional[np.ndarray], now: float) -> np.ndarray:
        """Compone el frame completo del tester."""
        canvas = np.full((WIN_H, WIN_W, 3), UI_BG, dtype=np.uint8)

        # Panel izquierdo
        self._draw_left_panel(canvas, cam_frame, now)

        # Título de sección ojos
        cv2.putText(canvas, "DISPLAY SIMULADO  ·  GC9A01  1.28\"  240×240",
                    (LEFT_W + 12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, UI_ACCENT, 1, cv2.LINE_AA)

        # Renderizar ojos
        left_eye  = self._render_eye_display(self._gaze_x, self._gaze_y, mirrored=False)
        right_eye = self._render_eye_display(self._gaze_x, self._gaze_y, mirrored=True)

        self._draw_bezel(canvas, left_eye,  EYE_L_CX, EYE_CY, "OJO IZQ")
        self._draw_bezel(canvas, right_eye, EYE_R_CX, EYE_CY, "OJO DER")

        # Paleta de emociones
        self._draw_emotion_palette(canvas)

        return canvas

    # ── Bucle principal ───────────────────────────────────────────────────────

    def run(self) -> None:
        """Bucle principal del simulador. Bloqueante hasta que el usuario sale."""
        print("\n[Tester] Iniciando simulador GC9A01...")
        if self._mtcnn:
            print("[Tester]  ✓ Detección de caras activa (MTCNN)")
        if self._ort:
            print("[Tester]  ✓ Clasificación de emociones activa (ONNX)")
        if not self._mtcnn:
            print("[Tester]  ! Sin MTCNN → instala facenet-pytorch para detección de caras")
        print("[Tester] Controles: Q/ESC=salir  1-8=emoción  B=parpadeo  M=ratón  D=demo\n")

        while self._running:
            now = time.time()

            cam_frame = self._update_state(now)

            canvas = self._compose_frame(cam_frame, now)
            cv2.imshow("GC9A01 Eye Simulator", canvas)

            key = cv2.waitKey(16) & 0xFF   # ~60 fps
            self._handle_key(key)

        cv2.destroyAllWindows()
        if self._cap:
            self._cap.release()
        print("[Tester] Simulador cerrado.")

    def _handle_key(self, key: int) -> None:
        if key in (ord('q'), ord('Q'), 27):   # Q o ESC
            self._running = False

        elif key == ord('b') or key == ord('B'):
            self._blink_start = time.time()

        elif key == ord('c') or key == ord('C'):
            self._show_cam = not self._show_cam

        elif key == ord('m') or key == ord('M'):
            self._follow_mouse = not self._follow_mouse
            print(f"[Tester] Seguir ratón: {'ON' if self._follow_mouse else 'OFF'}")

        elif key == ord('d') or key == ord('D'):
            self._demo_mode = not self._demo_mode
            print(f"[Tester] Modo demo: {'ON' if self._demo_mode else 'OFF'}")

        elif ord('1') <= key <= ord('8'):
            idx = key - ord('1')
            if idx < len(EMOTIONS):
                self._manual_emotion = True
                self._set_emotion(EMOTIONS[idx])
                print(f"[Tester] Emoción manual: {EMOTIONS[idx]}")

        elif key == ord('0'):
            self._manual_emotion = False
            print("[Tester] Emoción automática (detectada)")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador visual GC9A01 — ojos del robot R2")
    parser.add_argument("--camera", type=int, default=0, help="Índice de cámara (default: 0)")
    parser.add_argument("--demo",   action="store_true",  help="Modo demo sin cámara")
    args = parser.parse_args()

    tester = GC9A01Tester(camera_index=args.camera, demo_mode=args.demo)
    tester.run()


if __name__ == "__main__":
    main()
