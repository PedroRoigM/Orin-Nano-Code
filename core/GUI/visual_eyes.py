import cv2
import numpy as np
import time
import threading
import random
import math

# ─────────────────────────────────────────────────────────────────────────────
# Generador Procedimental de Polígonos de Ojos
# ─────────────────────────────────────────────────────────────────────────────

def generate_capsule(w: float, h: float, n_pts: int = 16) -> np.ndarray:
    """Genera el contorno de un rectángulo con bordes circulares (cápsula)."""
    r = w / 2.0
    straight_h = max(0.0, h - w)
    cy = straight_h / 2.0
    
    t1 = np.linspace(0, np.pi, n_pts, endpoint=False)
    arc_top = np.column_stack([r * np.cos(t1), -cy - r * np.sin(t1)])
    
    t2 = np.linspace(0, 1, n_pts, endpoint=False)
    left_str = np.column_stack([-r * np.ones_like(t2), -cy + t2 * (2 * cy)])
    
    t3 = np.linspace(np.pi, 2 * np.pi, n_pts, endpoint=False)
    arc_bot = np.column_stack([r * np.cos(t3), cy - r * np.sin(t3)])
    
    t4 = np.linspace(0, 1, n_pts, endpoint=False)
    right_str = np.column_stack([r * np.ones_like(t4), cy - t4 * (2 * cy)])
    
    return np.vstack([arc_top, left_str, arc_bot, right_str])

def generate_arc(r_out: float, r_in: float, cy_offset: float, n_pts: int = 16) -> np.ndarray:
    """Genera el contorno de un arco grueso, por ejemplo ^."""
    r_center = (r_out + r_in) / 2.0
    thick = r_out - r_in
    r_cap = thick / 2.0
    
    t1 = np.linspace(0, np.pi, n_pts, endpoint=False)
    arc_out = np.column_stack([r_out * np.cos(t1), cy_offset - r_out * np.sin(t1)])
    
    t2 = np.linspace(np.pi, 2 * np.pi, n_pts, endpoint=False)
    left_cap = np.column_stack([-r_center + r_cap * np.cos(t2), cy_offset - r_cap * np.sin(t2)])
    
    t3 = np.linspace(np.pi, 0, n_pts, endpoint=False)
    arc_in = np.column_stack([r_in * np.cos(t3), cy_offset - r_in * np.sin(t3)])
    
    t4 = np.linspace(np.pi, 2 * np.pi, n_pts, endpoint=False)
    right_cap = np.column_stack([r_center + r_cap * np.cos(t4), cy_offset - r_cap * np.sin(t4)])
    
    return np.vstack([arc_out, left_cap, arc_in, right_cap])

def get_target_poly(emotion: str) -> np.ndarray:
    """Mapea una emoción a los puntos del polígono correspondiente."""
    n_pts = 16
    
    # Valores por defecto para Neutral (Cápsula vertical, bloque blanco sólido)
    shape_type = "capsule"
    w = 70.0
    h = 110.0
    r_out = 40.0
    r_in = 10.0
    arc_dir = 1
    cy_offset = 0.0
    
    if emotion in ("neutral", "no_face"):
        pass
    elif emotion == "happiness":
        shape_type = "arc"     # ^
        arc_dir = 1
        cy_offset = 12.0
    elif emotion == "sadness":
        shape_type = "arc"     # U
        arc_dir = -1
        cy_offset = -12.0
    elif emotion == "anger":
        shape_type = "arc"     # U modificada
        arc_dir = -1
        cy_offset = -10.0
        r_out = 42.0
        r_in = 20.0
    elif emotion == "surprise":
        shape_type = "capsule"
        w = 76.0
        h = 126.0
    elif emotion in ("disgust", "contempt"):
        shape_type = "capsule"
        w = 66.0
        h = 80.0
        cy_offset = 5.0
    elif emotion == "fear":
        shape_type = "capsule"
        w = 64.0
        h = 100.0
        cy_offset = -10.0
        
    if shape_type == "capsule":
        pts = generate_capsule(w, h, n_pts)
        pts[:, 1] += cy_offset
    else:
        pts = generate_arc(r_out, r_in, 0, n_pts)
        if arc_dir == -1:
            pts[:, 1] = -pts[:, 1]  # Invertir para formar 'U'
        pts[:, 1] += cy_offset
        
    return pts

class RoboticEyeRenderer:
    """
    Generador de ojos robóticos con interpolación de polígonos.
    Al mutar las coordenadas de los vértices entre formas distintas,
    la transición simula fluidez anatómica (como achinarse o agrandarse),
    cumpliendo el patrón de "bloque continuo" en lugar de delgadas líneas de contorno.
    """
    
    SIZE = 240

    def __init__(self):
        self._lock = threading.Lock()
        
        self.tgt_emotion = "neutral"
        self.curr_pts = get_target_poly("neutral")
        
        self.gaze_x = 0.0
        self.gaze_y = 0.0
        self.tgt_gaze_x = 0.0
        self.tgt_gaze_y = 0.0
        
        # Parpadeo
        self.blink_start = None
        self.blink_factor = 1.0 # 1.0 = Abierto, 0.0 = Cerrado
        self.next_blink = time.time() + self._rand_blink()
        self.BLINK_DUR = 0.22

    @staticmethod
    def _rand_blink() -> float:
        return random.uniform(3.0, 7.0)

    def update(self, gaze_x: float, gaze_y: float, emotion: str) -> None:
        """Establece los objetivos de mirada y emoción."""
        with self._lock:
            self.tgt_emotion = emotion
            self.tgt_gaze_x = float(np.clip(gaze_x, -1.0, 1.0))
            self.tgt_gaze_y = float(np.clip(gaze_y, -1.0, 1.0))

    def set_idle(self) -> None:
        self.update(0.0, 0.0, "no_face")

    def get_frames(self) -> tuple[np.ndarray, np.ndarray]:
        """Devuelve (ojo_izquierdo, ojo_derecho) generados proceduralmente."""
        now = time.time()
        
        with self._lock:
            # LERP para suavidad en la mirada y forma
            L = 0.18
            self.gaze_x += (self.tgt_gaze_x - self.gaze_x) * L
            self.gaze_y += (self.tgt_gaze_y - self.gaze_y) * L
            
            tgt_pts = get_target_poly(self.tgt_emotion)
            # Morph fluido inter-puntos del polígono
            if self.curr_pts.shape == tgt_pts.shape:
                self.curr_pts += (tgt_pts - self.curr_pts) * L
            else:
                self.curr_pts = tgt_pts.copy()
            
            # Control de parpadeo
            if self.blink_start is None and now >= self.next_blink:
                self.blink_start = now
                
            if self.blink_start is not None:
                elapsed = now - self.blink_start
                half = self.BLINK_DUR / 2
                self.blink_factor = max(0.0, 1.0 - abs(elapsed - half) / half * 2)
                if elapsed > self.BLINK_DUR:
                    self.blink_factor = 1.0
                    self.blink_start = None
                    self.next_blink = now + self._rand_blink()
                    
            render_pts = self.curr_pts.copy()
            
            # Escala vertical comprimida simulando el cierre del párpado
            if self.blink_factor < 1.0:
                render_pts[:, 1] *= max(0.05, self.blink_factor)
                
            gx = int(self.gaze_x * 20)
            gy = int(self.gaze_y * 20)
            
            render_pts[:, 0] += gx
            render_pts[:, 1] += gy

        left_eye = self._render_one(render_pts)
        right_eye = self._render_one(render_pts)
        return left_eye, right_eye

    def _render_one(self, pts: np.ndarray) -> np.ndarray:
        S = self.SIZE
        img = np.zeros((S, S, 3), dtype=np.uint8)
        
        # Fondo oscuro para pantalla OLED
        img[:] = (12, 10, 10) 
        
        shifted_pts = pts.copy()
        shifted_pts[:, 0] += S // 2
        shifted_pts[:, 1] += S // 2
        
        # Formato bloque sólido blanco (sin generar pupilas raras)
        color = (255, 255, 255)
        cv2.fillPoly(img, [shifted_pts.astype(np.int32)], color, lineType=cv2.LINE_AA)
        
        return img


# ─────────────────────────────────────────────────────────────────────────────
# Controlador de Ventana de Interfaz Gráfica
# ─────────────────────────────────────────────────────────────────────────────
class RobotWindow:
    def __init__(self, frame_w: int, frame_h: int, eye_size: int = 240):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.eye_size = eye_size
        
        self.win_w = frame_w + 10 + eye_size
        self.win_h = frame_h
        
        self.eye_x = frame_w + 10
        self.eye_l_y = 0
        self.eye_r_y = frame_h // 2
        
        self.robot_eyes = RoboticEyeRenderer()
        
        cv2.namedWindow("Robot Medico", cv2.WINDOW_NORMAL)
        cv2.setWindowProperty("Robot Medico", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    def draw_eye_bezel(self, canvas: np.ndarray, x: int, y: int) -> None:
        """Dibuja el bisel decorativo circular simulando carcasa del robot."""
        size = self.eye_size
        cx, cy, r = x + size // 2, y + size // 2, size // 2
        cv2.circle(canvas, (cx, cy), r + 6,  (40, 40, 40), -1)   # anillo exterior
        cv2.circle(canvas, (cx, cy), r + 2,  (18, 14, 16), -1)   # interior oscuro
        # Reflejo sutil superior
        pts = np.array([
            [cx - r // 2, cy - r + 4],
            [cx + r // 2, cy - r + 4],
            [cx + r // 3, cy - r + 16],
            [cx - r // 3, cy - r + 16],
        ], np.int32)
        overlay = canvas.copy()
        cv2.fillPoly(overlay, [pts], (60, 60, 60))
        cv2.addWeighted(overlay, 0.25, canvas, 0.75, 0, canvas)

    def update_and_show(self, camera_frame: np.ndarray, fps: float, face_count: int, 
                        group_emotion: str, group_conf: float, hw_mode_str: str,
                        us_distance_str: str, behavior_tag: str, log_led: str):
        """Compone todos los elementos en una ventana unificada y la muestra."""
        canvas = np.zeros((self.win_h, self.win_w, 3), dtype=np.uint8)

        # 1. Pegar el frame de la cámara
        canvas[:self.frame_h, :self.frame_w] = camera_frame

        # 2. Generar y pegar los ojos robóticos
        eye_l, eye_r = self.robot_eyes.get_frames()
        
        # Dibujar biseles de carcasa
        self.draw_eye_bezel(canvas, self.eye_x, self.eye_l_y)
        self.draw_eye_bezel(canvas, self.eye_x, self.eye_r_y)
        
        # Para que los ojos solo se vean dentro del círculo (enmascarado)
        mask_l = np.zeros((self.eye_size, self.eye_size), dtype=np.uint8)
        mask_r = np.zeros((self.eye_size, self.eye_size), dtype=np.uint8)
        cv2.circle(mask_l, (self.eye_size//2, self.eye_size//2), self.eye_size//2, 255, -1)
        cv2.circle(mask_r, (self.eye_size//2, self.eye_size//2), self.eye_size//2, 255, -1)
        
        dest_l = canvas[self.eye_l_y:self.eye_l_y+self.eye_size, self.eye_x:self.eye_x+self.eye_size]
        dest_r = canvas[self.eye_r_y:self.eye_r_y+self.eye_size, self.eye_x:self.eye_x+self.eye_size]
        
        np.copyto(dest_l, eye_l, where=(mask_l > 0)[:, :, None])
        np.copyto(dest_r, eye_r, where=(mask_r > 0)[:, :, None])

        # 3. Separador y HUD
        canvas[:, self.frame_w:self.frame_w + 10] = (25, 25, 25)
        hud = f"FPS:{fps:.0f}  Faces:{face_count}  US:{us_distance_str}  [{hw_mode_str}] {group_emotion}"
        cv2.putText(canvas, hud, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # Info de ojos abajo
        cv2.putText(canvas, behavior_tag, (self.eye_x + 4, self.eye_r_y + self.eye_size - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.putText(canvas, f"conf={group_conf:.0%}  LED={log_led}",
                    (self.eye_x + 4, self.eye_r_y + self.eye_size - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1)

        cv2.imshow("Robot Medico", canvas)
