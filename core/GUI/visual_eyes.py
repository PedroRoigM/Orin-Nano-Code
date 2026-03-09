import cv2
import numpy as np
import time
import threading
import random
import math

# ─────────────────────────────────────────────────────────────────────────────
# Definición de Estados de los Ojos Robóticos
# ─────────────────────────────────────────────────────────────────────────────
# Cada estado se define por:
# r_x: radio horizontal
# r_y: radio vertical
# start: ángulo inicial de rotación (0 = abajo, 180 = arriba)
# end: ángulo final de rotación (360 = círculo completo)
# y_off: desplazamiento vertical respecto al centro

ROBOTIC_EYE_STATES = {
    "neutral":   {"r_x": 45, "r_y": 65, "start": 0,   "end": 360, "y_off": 0},
    "happiness": {"r_x": 45, "r_y": 50, "start": 180, "end": 360, "y_off": 15},
    "sadness":   {"r_x": 45, "r_y": 50, "start": 0,   "end": 180, "y_off": -15},
    "surprise":  {"r_x": 50, "r_y": 75, "start": 0,   "end": 360, "y_off": 0},
    "anger":     {"r_x": 45, "r_y": 40, "start": 0,   "end": 180, "y_off": -10}, 
    "disgust":   {"r_x": 45, "r_y": 35, "start": 0,   "end": 360, "y_off": 0}, 
    "fear":      {"r_x": 45, "r_y": 65, "start": 0,   "end": 360, "y_off": -5},
    "contempt":  {"r_x": 45, "r_y": 35, "start": 0,   "end": 360, "y_off": 0},
    "no_face":   {"r_x": 45, "r_y": 60, "start": 0,   "end": 360, "y_off": 0},
}

class RoboticEyeRenderer:
    """
    Nuevo generador de ojos robóticos. Usa formas geométricas simples:
    Óvalos para estado neutral, arcos superiores (^^) para felicidad,
    arcos inferiores (UU) para tristeza, y líneas horizontales para parpadeo.
    """
    
    SIZE = 240
    THICKNESS = 32

    def __init__(self):
        self._lock = threading.Lock()
        
        # Parámetros actuales (con suavizado)
        self.r_x = 45.0
        self.r_y = 65.0
        self.start = 0.0
        self.end = 360.0
        self.y_off = 0.0
        
        self.gaze_x = 0.0
        self.gaze_y = 0.0
        
        # Parámetros objetivo (target)
        self.tgt_r_x = 45.0
        self.tgt_r_y = 65.0
        self.tgt_start = 0.0
        self.tgt_end = 360.0
        self.tgt_y_off = 0.0
        
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
        state = ROBOTIC_EYE_STATES.get(emotion, ROBOTIC_EYE_STATES["neutral"])
        with self._lock:
            self.tgt_gaze_x = float(np.clip(gaze_x, -1.0, 1.0))
            self.tgt_gaze_y = float(np.clip(gaze_y, -1.0, 1.0))
            
            self.tgt_r_x = float(state["r_x"])
            self.tgt_r_y = float(state["r_y"])
            self.tgt_start = float(state["start"])
            self.tgt_end = float(state["end"])
            self.tgt_y_off = float(state["y_off"])

    def set_idle(self) -> None:
        self.update(0.0, 0.0, "no_face")

    def get_frames(self) -> tuple[np.ndarray, np.ndarray]:
        """Devuelve (ojo_izquierdo, ojo_derecho) generados proceduralmente."""
        now = time.time()
        
        with self._lock:
            # LERP para suavidad
            L = 0.18
            self.gaze_x += (self.tgt_gaze_x - self.gaze_x) * L
            self.gaze_y += (self.tgt_gaze_y - self.gaze_y) * L
            
            self.r_x += (self.tgt_r_x - self.r_x) * L
            self.r_y += (self.tgt_r_y - self.r_y) * L
            
            self.start += (self.tgt_start - self.start) * L
            self.end += (self.tgt_end - self.end) * L
            self.y_off += (self.tgt_y_off - self.y_off) * L
            
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
                    
            r_x = int(self.r_x)
            # El parpadeo aplasta r_y a 0
            r_y = max(1, int(self.r_y * self.blink_factor))
            start_ang = int(self.start)
            end_ang = int(self.end)
            y_off = int(self.y_off)
            
            # Gaze move max limits (20 px)
            gx = int(self.gaze_x * 20)
            gy = int(self.gaze_y * 20)

        left_eye = self._render_one(r_x, r_y, start_ang, end_ang, gx, gy, y_off)
        right_eye = self._render_one(r_x, r_y, start_ang, end_ang, gx, gy, y_off)
        return left_eye, right_eye

    def _render_one(self, r_x, r_y, start_ang, end_ang, gx, gy, y_off) -> np.ndarray:
        S = self.SIZE
        img = np.zeros((S, S, 3), dtype=np.uint8)
        
        # Fondo oscuro para pantalla OLED
        img[:] = (12, 10, 10) 
        
        # Centro base de la mirada y offset de estado
        cx = S // 2 + gx
        cy = S // 2 + gy + y_off
        
        color = (255, 255, 255) # Ojo blanco robótico
        
        if r_y <= 5: 
            # Es un parpadeo (línea plana con bordes redondeados)
            length = r_x + self.THICKNESS//2
            cv2.line(img, (cx - length, cy), (cx + length, cy), color, self.THICKNESS)
        else:
            # Forma de óvalo o arco
            cv2.ellipse(img, (cx, cy), (r_x, r_y), 0, start_ang, end_ang, color, self.THICKNESS, cv2.LINE_AA)
            
            # Si es un arco, añadir tapas redondeadas a los extremos para que quede perfecto
            if start_ang > 0 or end_ang < 360:
                # Calculamos el punto inicial
                p1_x = int(cx + r_x * math.cos(math.radians(start_ang)))
                p1_y = int(cy + r_y * math.sin(math.radians(start_ang)))
                cv2.circle(img, (p1_x, p1_y), self.THICKNESS//2, color, -1, cv2.LINE_AA)
                
                # Calculamos el punto final
                p2_x = int(cx + r_x * math.cos(math.radians(end_ang)))
                p2_y = int(cy + r_y * math.sin(math.radians(end_ang)))
                cv2.circle(img, (p2_x, p2_y), self.THICKNESS//2, color, -1, cv2.LINE_AA)

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
