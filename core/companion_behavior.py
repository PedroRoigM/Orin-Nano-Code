"""
companion_behavior.py
=====================
Diccionario de comportamiento del robot de acompañamiento médico.

FILOSOFÍA MÉDICA:
  El robot NO refuerza emociones negativas — responde con calma, calidez y presencia.
  Los colores y sonidos son COMPLEMENTARIOS al estado emocional del paciente:

    · Tristeza   → naranja cálido (≠ azul, que reforzaría la tristeza)
    · Ira        → azul sereno   (≠ rojo, que reforzaría la ira)
    · Miedo      → dorado cálido (≠ violeta, que reforzaría el miedo)
    · Asco       → lavanda suave neutra
    · Desprecio  → verde-azulado apaciguador
    · Alegría    → verde brillante (refuerzo positivo)
    · Sorpresa   → cian curioso

ESTRUCTURA de cada entrada en BEHAVIOR:
  "led"         str            "ON" | "OFF" | "BLINK"
                               LEDs simples Arduino (LED_1, LED_2, LED_3)

  "led_strip"   (R, G, B)     Color tira de LEDs NeoPixel/WS2812.
                               Stub presente — activar cuando el firmware lo soporte.

  "eyes_rgb"    (R, G, B)     Color terapéutico del iris en las pantallas GC9A01.
                               Enviado al Arduino vía EyesController (SERIAL).

  "eyes_squint" float 0–1     Nivel de entrecerrado del párpado (empatía, calma).
  "eyes_wide"   float 0–1     Apertura extra del iris (sorpresa, atención).

  "buzzer"      (Hz, ms)|None Tono del buzzer. None = silencio total.
                               Regla médica: emociones negativas de alta activación
                               → silencio (no irritar más). Graves suaves → calma.

  "lcd_line1"   str ≤16       Mensaje LCD, línea 1 (visible con firmware multi-línea).
  "lcd_line2"   str ≤16       Mensaje LCD, línea 2.

  "motor_pause" bool          True = detener el motor mientras reacciona.
                               Para emociones que requieren presencia quieta.

  "log_tag"     str           Etiqueta para el log de consola.

CÓMO EDITAR:
  Modifica los valores de este diccionario para ajustar el comportamiento del robot.
  Los cambios se aplican en el siguiente arranque (no requieren recompilación).
  Para añadir nuevas emociones, agregar una clave al dict BEHAVIOR con todos los campos.
"""

from typing import Optional
import time

# ─────────────────────────────────────────────────────────────────────────────
# Paleta terapéutica para iris de los ojos (GC9A01, RGB)
# Diseñada para CALMAR, no para espejar la emoción del paciente.
# ─────────────────────────────────────────────────────────────────────────────
_EYE_NEUTRAL   = (200, 200, 180)  # blanco cálido tenue — standby relajado
_EYE_HAPPINESS = (100, 220,  80)  # verde brillante — refuerzo positivo
_EYE_SURPRISE  = ( 80, 200, 200)  # cian curioso — atención abierta
_EYE_SADNESS   = (255, 165,  50)  # naranja cálido — calor reconfortante (≠ azul-tristeza)
_EYE_ANGER     = ( 70, 150, 255)  # azul serenidad — calma opuesta a la ira
_EYE_DISGUST   = (180, 140, 220)  # lavanda — neutralidad suave
_EYE_FEAR      = (255, 200,  70)  # dorado cálido — seguridad (≠ violeta-miedo)
_EYE_CONTEMPT  = (110, 195, 185)  # verde-azulado — apaciguador

# ─────────────────────────────────────────────────────────────────────────────
# Paleta para tira de LEDs NeoPixel/WS2812 (RGB)
# Misma filosofía: colores complementarios para calmar.
# Intensidades bajas para no resultar invasivos en entornos clínicos.
# ─────────────────────────────────────────────────────────────────────────────
_STRIP_NEUTRAL   = ( 50,  45,  30)  # ámbar muy tenue — standby
_STRIP_HAPPINESS = (  0, 160,  20)  # verde suave
_STRIP_SURPRISE  = (  0, 140, 140)  # cian suave
_STRIP_SADNESS   = (180,  70,   0)  # naranja cálido suave
_STRIP_ANGER     = (  0,  35, 160)  # azul tranquilo
_STRIP_DISGUST   = ( 90,  50, 140)  # lavanda tenue
_STRIP_FEAR      = (160, 120,   0)  # dorado suave
_STRIP_CONTEMPT  = ( 35, 120, 120)  # verde-azulado tenue

# ─────────────────────────────────────────────────────────────────────────────
# BEHAVIOR — Diccionario principal de comportamiento
# Edita este diccionario para personalizar la respuesta del robot.
# ─────────────────────────────────────────────────────────────────────────────
BEHAVIOR: dict[str, dict] = {

    # ── Neutral ───────────────────────────────────────────────────────────────
    "neutral": {
        "led":          "OFF",
        "led_strip":    _STRIP_NEUTRAL,
        "eyes_rgb":     _EYE_NEUTRAL,
        "eyes_squint":  0.00,
        "eyes_wide":    0.00,
        "buzzer":       None,
        "lcd_line1":    "Hola :)",
        "lcd_line2":    "Estoy aqui",
        "motor_pause":  False,
        "log_tag":      "NEUTRAL",
    },

    # ── Alegría — refuerzo positivo ───────────────────────────────────────────
    "happiness": {
        "led":          "ON",
        "led_strip":    _STRIP_HAPPINESS,
        "eyes_rgb":     _EYE_HAPPINESS,
        "eyes_squint":  0.00,
        "eyes_wide":    0.20,           # ojos más abiertos, expresivos
        "buzzer":       (660, 120),     # La (A5) — alegre y suave
        "lcd_line1":    "Que alegria!",
        "lcd_line2":    "Me alegra verte",
        "motor_pause":  False,
        "log_tag":      "HAPPY",
    },

    # ── Sorpresa — atención curiosa ───────────────────────────────────────────
    "surprise": {
        "led":          "ON",
        "led_strip":    _STRIP_SURPRISE,
        "eyes_rgb":     _EYE_SURPRISE,
        "eyes_squint":  0.00,
        "eyes_wide":    0.50,           # ojos muy abiertos
        "buzzer":       (520, 80),      # Do (C5) — corto, curioso
        "lcd_line1":    "Oh! Hola!",
        "lcd_line2":    "No te vi!",
        "motor_pause":  False,
        "log_tag":      "SURPRISE",
    },

    # ── Tristeza — presencia cálida y reconfortante ───────────────────────────
    # Regla: luz ESTABLE (presencia), naranja cálido (≠ azul que refuerza tristeza)
    "sadness": {
        "led":          "ON",           # luz estable = presencia reconfortante
        "led_strip":    _STRIP_SADNESS,
        "eyes_rgb":     _EYE_SADNESS,   # naranja cálido ≠ azul-tristeza
        "eyes_squint":  0.12,           # ligeramente entrecerrado (empatía)
        "eyes_wide":    0.00,
        "buzzer":       (330, 350),     # Mi grave (E4) — tono suave reconfortante
        "lcd_line1":    "Estoy contigo",
        "lcd_line2":    "Todo va bien",
        "motor_pause":  True,           # detenerse = estar presente, acompañar
        "log_tag":      "SADNESS",
    },

    # ── Ira — desescalada total ───────────────────────────────────────────────
    # Regla: mínima estimulación, silencio, azul sereno (≠ rojo que refuerza ira)
    "anger": {
        "led":          "OFF",          # apagar = reducir estimulación visual
        "led_strip":    _STRIP_ANGER,
        "eyes_rgb":     _EYE_ANGER,     # azul sereno ≠ rojo-ira
        "eyes_squint":  0.08,           # expresión calmada, no agresiva
        "eyes_wide":    0.00,
        "buzzer":       None,           # silencio total — no irritar más
        "lcd_line1":    "Respira...",
        "lcd_line2":    "Con calma",
        "motor_pause":  True,           # quieto = no amenazante
        "log_tag":      "ANGER",
    },

    # ── Asco — neutralidad calmante ───────────────────────────────────────────
    "disgust": {
        "led":          "OFF",
        "led_strip":    _STRIP_DISGUST,
        "eyes_rgb":     _EYE_DISGUST,
        "eyes_squint":  0.08,
        "eyes_wide":    0.00,
        "buzzer":       None,
        "lcd_line1":    "Entiendo...",
        "lcd_line2":    "Aqui estoy",
        "motor_pause":  False,
        "log_tag":      "DISGUST",
    },

    # ── Miedo — presencia cálida y segura ────────────────────────────────────
    # Regla: luz estable (tranquiliza), dorado cálido (≠ violeta que refuerza miedo)
    "fear": {
        "led":          "ON",           # luz estable = reconfortante, no parpadear
        "led_strip":    _STRIP_FEAR,
        "eyes_rgb":     _EYE_FEAR,      # dorado cálido ≠ violeta-miedo
        "eyes_squint":  0.00,
        "eyes_wide":    0.10,           # ligeramente abierto = atento y cálido
        "buzzer":       (392, 180),     # Sol (G4) — tono musical reconfortante
        "lcd_line1":    "Estoy aqui",
        "lcd_line2":    "No hay peligro",
        "motor_pause":  True,           # no moverse = no asustar más
        "log_tag":      "FEAR",
    },

    # ── Desprecio — apaciguador neutro ───────────────────────────────────────
    "contempt": {
        "led":          "OFF",
        "led_strip":    _STRIP_CONTEMPT,
        "eyes_rgb":     _EYE_CONTEMPT,
        "eyes_squint":  0.05,
        "eyes_wide":    0.00,
        "buzzer":       None,
        "lcd_line1":    "Hola",
        "lcd_line2":    "Cuentame",
        "motor_pause":  False,
        "log_tag":      "CONTEMPT",
    },

    # ── Sin cara — modo espera soñoliento ─────────────────────────────────────
    "no_face": {
        "led":          "OFF",
        "led_strip":    _STRIP_NEUTRAL,
        "eyes_rgb":     _EYE_NEUTRAL,
        "eyes_squint":  0.25,           # semicerrado = soñoliento, en espera
        "eyes_wide":    0.00,
        "buzzer":       None,
        "lcd_line1":    "Buscando...",
        "lcd_line2":    "",
        "motor_pause":  False,
        "log_tag":      "NO_FACE",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Parámetros de filtrado
# ─────────────────────────────────────────────────────────────────────────────

# Confianza mínima del clasificador para considerar la emoción válida.
# Lecturas por debajo se tratan como "neutral".
EMOTION_CONFIDENCE_THRESHOLD: float = 0.60

# Nº de frames consecutivos con la misma emoción antes de activar los actuadores.
# Evita parpadeos y reacciones a lecturas aisladas.
EMOTION_STABILITY_FRAMES: int = 4


# ─────────────────────────────────────────────────────────────────────────────
# BehaviorEngine — motor de comportamiento
# ─────────────────────────────────────────────────────────────────────────────
class BehaviorEngine:
    """
    Aplica el diccionario BEHAVIOR a todos los controladores hardware.

    Incluye:
      · Filtro de confianza mínima (EMOTION_CONFIDENCE_THRESHOLD)
      · Filtro de estabilidad temporal (EMOTION_STABILITY_FRAMES) — anti-parpadeo
      · Actualización continua de ojos (gaze sigue la cara frame a frame)
      · Activación puntual de LEDs, buzzer y LCD solo al cambiar de estado

    Uso:
        engine = BehaviorEngine(arduino=arduino, eyes=arduino.eyes)
        engine.apply("sadness", conf=0.82, face_cx=310, face_cy=220)
        engine.apply("no_face")   # sin cara detectada
    """

    def __init__(self, arduino=None, eyes=None) -> None:
        """
        Args:
            arduino : ArduinoController — None en modo simulación sin hardware.
            eyes    : EyesController    — normalmente arduino.eyes; None si no disponible.
        """
        self._arduino      = arduino
        self._eyes         = eyes
        self._last_emotion = ""   # última emoción recibida (para conteo)
        self._stable_count = 0    # frames consecutivos con la misma emoción
        self._prev_emotion = ""   # última emoción que llegó a los actuadores
        self._last_eyes_update = time.time()

    # ── API pública ───────────────────────────────────────────────────────────

    def apply(
        self,
        emotion:  str,
        conf:     float = 1.0,
        gaze_x:   float = 0.0,
        gaze_y:   float = 0.0,
        face_cx:  Optional[int] = None,
        face_cy:  Optional[int] = None,
        frame_w:  int = 640,
        frame_h:  int = 480,
    ) -> bool:
        """
        Aplica el comportamiento asociado a la emoción detectada.

        Los ojos se actualizan en cada llamada (seguimiento continuo).
        LEDs, buzzer y LCD solo se activan cuando el estado cambia y es estable.

        Returns:
            True si el estado de actuadores cambió (emoción nueva y estable).
        """
        # 1. Filtro de confianza (no aplica a "no_face")
        if emotion not in ("no_face", "unknown"):
            if conf < EMOTION_CONFIDENCE_THRESHOLD:
                emotion = "neutral"

        # 2. Calcular gaze desde posición de cara en píxeles
        if face_cx is not None:
            gaze_x = (face_cx - frame_w / 2) / (frame_w / 2)
        if face_cy is not None:
            gaze_y = (face_cy - frame_h / 2) / (frame_h / 2)

        # 3. Actualizar ojos — sin filtro de estabilidad (seguimiento fluido)
        self._update_eyes(emotion, gaze_x, gaze_y)

        # 4. Filtro de estabilidad para actuadores
        if emotion == self._last_emotion:
            self._stable_count += 1
        else:
            self._stable_count = 1
            self._last_emotion = emotion

        if self._stable_count < EMOTION_STABILITY_FRAMES:
            return False   # aún no confirmada

        # 5. Solo aplicar si es realmente nuevo
        if emotion == self._prev_emotion:
            return False   # sin cambio de estado

        self._prev_emotion = emotion
        b = BEHAVIOR.get(emotion, BEHAVIOR["neutral"])
        self._apply_leds(b)
        self._apply_buzzer(b)
        return True

    def apply_immediate(
        self,
        emotion: str,
        conf:    float = 1.0,
        gaze_x:  float = 0.0,
        gaze_y:  float = 0.0,
    ) -> None:
        """
        Aplica el comportamiento sin filtros de estabilidad.
        Útil para respuestas a eventos puntuales (obstáculo, arranque, etc.).
        """
        b = BEHAVIOR.get(emotion, BEHAVIOR["neutral"])
        self._update_eyes(emotion, gaze_x, gaze_y)
        self._apply_leds(b)
        self._apply_buzzer(b)
        self._prev_emotion = emotion

    def motor_should_pause(self, emotion: str) -> bool:
        """
        True si la emoción actual requiere que el motor permanezca detenido.
        Usar en drive_toward_face() para respetar el comportamiento médico.
        """
        return BEHAVIOR.get(emotion, {}).get("motor_pause", False)

    def get_led_strip_color(self, emotion: str) -> tuple[int, int, int]:
        """Devuelve el color RGB para la tira de LEDs según la emoción."""
        return BEHAVIOR.get(emotion, BEHAVIOR["neutral"]).get(
            "led_strip", _STRIP_NEUTRAL
        )

    @property
    def current_emotion(self) -> str:
        """Última emoción confirmada (aplicada a actuadores)."""
        return self._prev_emotion or "neutral"

    # ── Internos ──────────────────────────────────────────────────────────────

    def _update_eyes(self, emotion: str, gaze_x: float, gaze_y: float) -> None:
        """
        Actualiza mirada y color terapéutico en el controlador de ojos.
        Limitado a máximo 2 actualizaciones por segundo (500ms entre llamadas).
        El propio controlador (EyesController / MockEyes) gestiona el logging
        [SERIAL →] y el filtro de cambio de emoción internamente.
        """
        if self._eyes is None:
            return

        # Rate limiting: máximo 2 veces por segundo (500ms)
        current_time = time.time()
        if current_time - self._last_eyes_update < 0.5:
            return
        self._last_eyes_update = current_time

        if emotion == "no_face":
            if hasattr(self._eyes, "set_idle"):
                self._eyes.set_idle()
        else:
            if hasattr(self._eyes, "update"):
                beh = BEHAVIOR.get(emotion, BEHAVIOR["neutral"])
                rgb = beh.get("eyes_rgb", _EYE_NEUTRAL)
                self._eyes.update(gaze_x, gaze_y, emotion, iris_color_override=rgb)

    def _apply_leds(self, b: dict) -> None:
        if self._arduino is None:
            return
        cmd = b.get("led", "OFF")
        if cmd == "ON":
            self._arduino.leds.on()
        elif cmd == "BLINK":
            self._arduino.leds.blink()
        else:
            self._arduino.leds.off()

    def _apply_buzzer(self, b: dict) -> None:
        if self._arduino is None:
            return
        tone = b.get("buzzer")
        if tone is None:
            return
        freq, ms = tone
        self._arduino.buzzer.tone(freq, ms)

    def _apply_lcd(self, b: dict) -> None:
        if self._arduino is None:
            return
        l1 = b.get("lcd_line1", "")
        l2 = b.get("lcd_line2", "")
        if l2:
            self._arduino.lcd.display_two_lines(l1[:16], l2[:16])
        elif l1:
            self._arduino.lcd.display_text(l1[:16])
