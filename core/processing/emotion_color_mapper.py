class EmotionColorMapper:

    def __init__(self):
        self.russell_colors = {
            "Activa/Positiva":  (255, 220, 0),
            "Pasiva/Positiva":  (0,   180, 255),
            "Activa/Negativa":  (255, 30,  30),
            "Pasiva/Negativa":  (30,  30,  120),
        }

        # 8 emociones del modelo FER+
        self.emotion_colors = {
            "neutral":   (200, 200, 200),
            "happiness": (0,   255, 0),
            "surprise":  (0,   255, 255),
            "sadness":   (255, 0,   0),
            "anger":     (0,   0,   255),
            "disgust":   (0,   128, 0),
            "fear":      (128, 0,   128),
            "contempt":  (128, 128, 0),
        }

        # Circumplex de Russell: (valence, arousal) por emoción
        # valence: -1 negativo → +1 positivo
        # arousal: -1 pasivo   → +1 activo
        self._RUSSELL_MAP = {
            "neutral":   ( 0.0,  0.0),
            "happiness": ( 0.9,  0.6),
            "surprise":  ( 0.2,  0.8),
            "sadness":   (-0.8, -0.5),
            "anger":     (-0.7,  0.8),
            "disgust":   (-0.6,  0.3),
            "fear":      (-0.7,  0.7),
            "contempt":  (-0.5,  0.1),
        }

        self._EXCLUDE = {"valence", "arousal", "categoria_russell"}

    # ------------------------------------------------------------------

    def _categorize_russell(self, valence: float, arousal: float) -> str:
        if valence >= 0 and arousal >= 0:
            return "Activa/Positiva"
        elif valence >= 0 and arousal < 0:
            return "Pasiva/Positiva"
        elif valence < 0 and arousal >= 0:
            return "Activa/Negativa"
        else:
            return "Pasiva/Negativa"

    def build_emotions_dict(self, emotion: str, confidence: float) -> dict:
        """
        Construye el dict de emociones a partir del output del modelo
        (emoción dominante + confianza). El resto de emociones se
        inicializan a 0 para mantener compatibilidad con los métodos.
        """
        scores = {e: 0.0 for e in self.emotion_colors}
        scores[emotion] = confidence

        v, a = self._RUSSELL_MAP.get(emotion, (0.0, 0.0))
        scores["valence"] = v
        scores["arousal"] = a
        scores["categoria_russell"] = self._categorize_russell(v, a)
        return scores

    # ------------------------------------------------------------------

    def get_russell_color(self, emotions: dict) -> tuple:
        category = emotions.get("categoria_russell", "")
        return self.russell_colors.get(category, (128, 128, 128))

    def get_dominant_emotion_color(self, emotions: dict) -> tuple[tuple, str]:
        scores = {
            k: v for k, v in emotions.items()
            if k not in self._EXCLUDE and k in self.emotion_colors
        }
        if not scores:
            return (128, 128, 128), "neutral"
        dominant = max(scores, key=scores.get)
        return self.emotion_colors[dominant], dominant

    def get_valence_arousal_color(self, emotions: dict) -> tuple:
        valence = emotions.get("valence", 0.0)
        arousal = emotions.get("arousal", 0.0)
        v = (valence + 1) / 2.0
        a = (arousal + 1) / 2.0
        brightness = 0.4 + 0.6 * a
        if v >= 0.5:
            r = int(255 * brightness)
            g = int(200 * brightness * (2 - v * 2 + 0.5))
            b = int(80  * brightness * (1 - v))
        else:
            r = int(180 * brightness * v * 2)
            g = int(80  * brightness * v * 2)
            b = int(255 * brightness)
        return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

    def rgb_to_hex(self, rgb: tuple) -> str:
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    def get_color_dict(self, emotion: str, confidence: float) -> dict:
        emotions = self.build_emotions_dict(emotion, confidence)
        russell  = self.get_russell_color(emotions)
        dominant_color, dominant_name = self.get_dominant_emotion_color(emotions)
        va       = self.get_valence_arousal_color(emotions)
        return {
            "russell_rgb":         russell,
            "russell_hex":         self.rgb_to_hex(russell),
            "dominant_rgb":        dominant_color,
            "dominant_hex":        self.rgb_to_hex(dominant_color),
            "dominant_emotion":    dominant_name,
            "valence_arousal_rgb": va,
            "valence_arousal_hex": self.rgb_to_hex(va),
            "valence":             emotions["valence"],
            "arousal":             emotions["arousal"],
            "categoria_russell":   emotions["categoria_russell"],
        }