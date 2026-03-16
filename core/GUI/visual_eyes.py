import cv2
import numpy as np
import time
import threading
import random

# ─────────────────────────────────────────────────────────────────────────────
# Configuración de Temas (Colores y Dimensiones XXL para Pupilas)
# ─────────────────────────────────────────────────────────────────────────────

EMOTION_THEMES = {
    # Dimensiones aumentadas significativamente para máxima expresividad
    "neutral":   {"bg": (205, 195, 202), "eye_w": 65, "eye_h": 100, "tilt": 0},
    "no_face":   {"bg": (205, 195, 202), "eye_w": 65, "eye_h": 100, "tilt": 0},
    "anger":     {"bg": (250, 250, 200), "eye_w": 70, "eye_h": 85,  "tilt": 25}, 
    "contempt":  {"bg": (210, 230, 145), "eye_w": 80, "eye_h": 65,  "tilt": 0},   
    "fear":      {"bg": (215, 255, 245), "eye_w": 55, "eye_h": 100, "tilt": 0},   
    "disgust":   {"bg": (160, 255, 235), "eye_w": 70, "eye_h": 70,  "tilt": 0},   
    "sadness":   {"bg": (160, 215, 255), "eye_w": 65, "eye_h": 100, "tilt": -20}, 
    "happiness": {"bg": (140, 180, 255), "eye_w": 85, "eye_h": 75,  "tilt": 0},   
    "surprise":  {"bg": (245, 190, 190), "eye_w": 55, "eye_h": 120, "tilt": 0},   
}

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de Dibujo
# ─────────────────────────────────────────────────────────────────────────────

def draw_capsule(img, center, w, h, color, angle_deg=0):
    """Dibuja una cápsula (pupila blanca) con rotación y suavizado."""
    n_pts = 16
    r = w / 2
    sh = max(0.0, (h - w) / 2.0)
    
    pts = []
    # Generar contorno de cápsula
    for a in np.linspace(0, np.pi, n_pts):
        pts.append([r * np.cos(a), -sh - r * np.sin(a)])
    for a in np.linspace(np.pi, 2 * np.pi, n_pts):
        pts.append([r * np.cos(a), sh - r * np.sin(a)])
    
    pts = np.array(pts, dtype=np.float32)
    
    # Aplicar rotación emocional
    if angle_deg != 0:
        rad = np.radians(angle_deg)
        c, s = np.cos(rad), np.sin(rad)
        rot_mat = np.array([[c, -s], [s, c]])
        pts = pts @ rot_mat.T
    
    # Traslación a posición de mirada
    pts[:, 0] += center[0]
    pts[:, 1] += center[1]
    
    cv2.fillPoly(img, [pts.astype(np.int32)], color, lineType=cv2.LINE_AA)

class RoboticEyeRenderer:
    """Renderiza el ojo integrando el fondo total del color de la emoción."""
    SIZE = 240

    def __init__(self):
        self._lock = threading.Lock()
        self.tgt_emotion = "neutral"
        
        self.eye_w = 65.0
        self.eye_h = 100.0
        self.bg_color = np.array([205.0, 195.0, 202.0], dtype=np.float32)
        
        self.gaze_x, self.gaze_y = 0.0, 0.0
        self.tgt_gaze_x, self.tgt_gaze_y = 0.0, 0.0
        
        self.blink_start = None
        self.blink_factor = 1.0
        self.next_blink = time.time() + random.uniform(3, 7)
        self.BLINK_DUR = 0.15

    def update(self, gaze_x: float, gaze_y: float, emotion: str) -> None:
        with self._lock:
            if emotion in EMOTION_THEMES:
                self.tgt_emotion = emotion
            self.tgt_gaze_x = float(np.clip(gaze_x, -1.0, 1.0))
            self.tgt_gaze_y = float(np.clip(gaze_y, -1.0, 1.0))

    def get_frames(self) -> tuple[np.ndarray, np.ndarray]:
        now = time.time()
        with self._lock:
            # Interpolación para transiciones suaves
            L = 0.2 
            self.gaze_x += (self.tgt_gaze_x - self.gaze_x) * L
            self.gaze_y += (self.tgt_gaze_y - self.gaze_y) * L
            
            theme = EMOTION_THEMES[self.tgt_emotion]
            self.eye_w += (theme["eye_w"] - self.eye_w) * L
            self.eye_h += (theme["eye_h"] - self.eye_h) * L
            
            target_bg = np.array(theme["bg"], dtype=np.float32)
            self.bg_color += (target_bg - self.bg_color) * L
            
            # Lógica de parpadeo rápida
            if self.blink_start is None and now >= self.next_blink:
                self.blink_start = now
            if self.blink_start is not None:
                elapsed = now - self.blink_start
                half = self.BLINK_DUR / 2
                self.blink_factor = max(0.0, abs(elapsed - half) / half)
                if elapsed > self.BLINK_DUR:
                    self.blink_factor = 1.0
                    self.blink_start = None
                    self.next_blink = now + random.uniform(4, 9)
            else:
                self.blink_factor = 1.0

            curr_bg = (int(self.bg_color[0]), int(self.bg_color[1]), int(self.bg_color[2]))

        img_l = self._render_one(theme, curr_bg, is_left=True)
        img_r = self._render_one(theme, curr_bg, is_left=False)
        return img_l, img_r

    def _render_one(self, theme, bg_color, is_left) -> np.ndarray:
        S = self.SIZE
        img = np.zeros((S, S, 3), dtype=np.uint8)
        
        # EL OJO AHORA TIENE EL FONDO COMPLETO DEL COLOR DE LA EMOCIÓN
        img[:] = bg_color 

        cx, cy = S // 2, S // 2
        # Contenedor interno (un tono ligeramente más oscuro para dar profundidad, opcional)
        # Aquí lo mantendremos igual al fondo para el look de "ojos integrados"
        cont_w, cont_h = 200, 130
        
        # Mirada amplia
        gx, gy = self.gaze_x * 50, self.gaze_y * 15
        tilt = theme["tilt"] if is_left else -theme["tilt"]
        h_blink = self.eye_h * self.blink_factor
        
        # Pupila blanca gigante
        draw_capsule(img, (cx + gx, cy + gy), self.eye_w, h_blink, (255, 255, 255), tilt)

        return img
    
    def set_idle(self):
        with self._lock:
            self.tgt_emotion = "no_face"
            self.tgt_gaze_x = 0.0
            self.tgt_gaze_y = 0.0

# ─────────────────────────────────────────────────────────────────────────────
# Controlador de Ventana (GUI Principal)
# ─────────────────────────────────────────────────────────────────────────────
class RobotWindow:
    def __init__(self, frame_w: int, frame_h: int, eye_size: int = 240):
        self.frame_w, self.frame_h = frame_w, frame_h
        self.eye_size = eye_size
        self.win_w = frame_w + 10 + eye_size
        self.win_h = frame_h
        self.eye_x = frame_w + 10
        self.eye_l_y, self.eye_r_y = 0, frame_h // 2
        
        self.robot_eyes = RoboticEyeRenderer()
        cv2.namedWindow("Robot Medico", cv2.WINDOW_NORMAL)

    def update_and_show(self, camera_frame, fps, face_count, group_emotion, gaze_x=0.0, gaze_y=0.0):
        # 1. Obtener color del tema actual
        theme = EMOTION_THEMES.get(group_emotion, EMOTION_THEMES["neutral"])
        bg_color = (int(theme["bg"][0]), int(theme["bg"][1]), int(theme["bg"][2]))
        
        # 2. Inicializar canvas con el color de la emoción (TODO el fondo)
        canvas = np.full((self.win_h, self.win_w, 3), bg_color, dtype=np.uint8)
        
        # 3. Pegar frame de cámara
        if camera_frame is not None:
            canvas[:self.frame_h, :self.frame_w] = camera_frame

        # 4. Generar y pegar ojos
        self.robot_eyes.update(gaze_x, gaze_y, group_emotion)
        eye_l, eye_r = self.robot_eyes.get_frames()
        
        # Máscara circular para los ojos
        mask = np.zeros((self.eye_size, self.eye_size), dtype=np.uint8)
        cv2.circle(mask, (self.eye_size//2, self.eye_size//2), self.eye_size//2, 255, -1)
        
        for i, img_eye in enumerate([eye_l, eye_r]):
            y_off = self.eye_l_y if i == 0 else self.eye_r_y
            
            # Dibujar un borde de "bisel" para definir el círculo del ojo
            cx_eye, cy_eye = self.eye_x + self.eye_size//2, y_off + self.eye_size//2
            cv2.circle(canvas, (cx_eye, cy_eye), self.eye_size//2 + 2, (30, 30, 30), 2, cv2.LINE_AA)
            
            roi = canvas[y_off:y_off+self.eye_size, self.eye_x:self.eye_x+self.eye_size]
            np.copyto(roi, img_eye, where=(mask > 0)[:, :, None])

        # 5. HUD Superior (Fondo negro para legibilidad)
        cv2.rectangle(canvas, (0, 0), (self.frame_w, 35), (10, 10, 10), -1)
        hud = f"FPS:{fps:.0f} | FACES:{face_count} | EMOTION: {group_emotion.upper()}"
        cv2.putText(canvas, hud, (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        cv2.imshow("Robot Medico", canvas)
