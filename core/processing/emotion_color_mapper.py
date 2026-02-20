class EmotionColorMapper:

    def __init__(self):
        # Keys deben coincidir EXACTAMENTE con classifier._categorize_russell
        self.russell_colors = {
            "Activa/Positiva":  (255, 220, 0),    # amarillo puro, muy brillante
            "Pasiva/Positiva":  (0,   180, 255),  # azul cian brillante
            "Activa/Negativa":  (255, 30,  30),   # rojo puro, intenso
            "Pasiva/Negativa":  (30,  30,  120),  # azul muy oscuro
        }

        self.emotion_colors = {
            "attention":  (255, 200, 0),    # dorado brillante
            "meditation": (120, 80,  220),  # púrpura medio
            "calma":      (0,   160, 255),  # azul brillante
            "serenidad":  (0,   220, 150),  # verde esmeralda
            "foco":       (255, 140, 0),    # naranja intenso
            "estres":     (255, 0,   0),    # rojo puro
            "excitacion": (255, 80,  0),    # naranja-rojo
            "felicidad":  (255, 255, 0),    # amarillo máximo
            "fatiga":     (40,  20,  80),   # púrpura muy oscuro
        }

        # Emociones válidas para mezcla (excluir metadatos del dict)
        self._EXCLUDE = {"valence", "arousal", "categoria_russell"}

    # ------------------------------------------------------------------

    def get_russell_color(self, emotions: dict) -> tuple:
        category = emotions.get("categoria_russell", "")
        return self.russell_colors.get(category, (128, 128, 128))

    def get_top3_blended_color(self, emotions: dict) -> tuple:
        """
        Mezcla los colores de las 3 emociones más dominantes,
        ponderando por score^2 para dar más peso a la dominante.
        """
        scores = {
            k: v for k, v in emotions.items()
            if k not in self._EXCLUDE
            and k in self.emotion_colors
            and isinstance(v, (int, float))
        }
        top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]

        if not top3:
            return (128, 128, 128)

        total = sum(s ** 2 for _, s in top3)
        if total == 0:
            return (128, 128, 128)

        r, g, b = 0.0, 0.0, 0.0
        for name, score in top3:
            w = (score ** 2) / total
            cr, cg, cb = self.emotion_colors[name]
            r += cr * w
            g += cg * w
            b += cb * w

        return (int(r), int(g), int(b))

    def get_top3_info(self, emotions: dict) -> list:
        """Devuelve [(nombre, score, color_rgb), ...] para las top 3."""
        scores = {
            k: v for k, v in emotions.items()
            if k not in self._EXCLUDE
            and k in self.emotion_colors
            and isinstance(v, (int, float))
        }
        top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        return [(name, score, self.emotion_colors[name]) for name, score in top3]

    def get_dominant_emotion_color(self, emotions: dict) -> tuple:
        scores = {
            k: v for k, v in emotions.items()
            if k not in self._EXCLUDE and k in self.emotion_colors
        }
        if not scores:
            return (128, 128, 128), "neutral"
        dominant = max(scores, key=scores.get)
        return self.emotion_colors[dominant], dominant

    def get_valence_arousal_color(self, emotions: dict) -> tuple:
        """
        Usa directamente valence/arousal del classifier (ya calculados)
        en lugar de recalcularlos desde emociones individuales.
        
        valence: -1.0 (negativo) a +1.0 (positivo)
        arousal: -1.0 (pasivo)   a +1.0 (activo)
        """
        valence = emotions.get("valence", 0.0)  # ya está en -1..1
        arousal = emotions.get("arousal", 0.0)

        # Normalizar a 0-1
        v = (valence + 1) / 2.0
        a = (arousal + 1) / 2.0

        brightness = 0.4 + 0.6 * a  # arousal alto = más brillante

        if v >= 0.5:  # valencia positiva → amarillo/naranja
            r = int(255 * brightness)
            g = int(200 * brightness * (2 - v * 2 + 0.5))
            b = int(80  * brightness * (1 - v))
        else:         # valencia negativa → azul/rojo
            r = int(180 * brightness * v * 2)
            g = int(80  * brightness * v * 2)
            b = int(255 * brightness)

        return (
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b)),
        )

    def get_blended_color(self, emotions: dict) -> tuple:
        """Mezcla todas las emociones ponderadas por intensidad."""
        r, g, b, total = 0.0, 0.0, 0.0, 0.0
        for name, color in self.emotion_colors.items():
            intensity = emotions.get(name, 0) / 100.0
            if intensity > 0.1:
                r += color[0] * intensity
                g += color[1] * intensity
                b += color[2] * intensity
                total += intensity
        if total == 0:
            return (128, 128, 128)
        return (int(r / total), int(g / total), int(b / total))

    def rgb_to_hex(self, rgb: tuple) -> str:
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    def get_color_dict(self, emotions: dict) -> dict:
        russell   = self.get_russell_color(emotions)
        top3      = self.get_top3_blended_color(emotions)
        dominant_color, dominant_name = self.get_dominant_emotion_color(emotions)
        va        = self.get_valence_arousal_color(emotions)
        return {
            "russell_rgb":        russell,
            "russell_hex":        self.rgb_to_hex(russell),
            "top3_blended_rgb":   top3,
            "top3_blended_hex":   self.rgb_to_hex(top3),
            "dominant_rgb":       dominant_color,
            "dominant_hex":       self.rgb_to_hex(dominant_color),
            "dominant_emotion":   dominant_name,
            "valence_arousal_rgb": va,
            "valence_arousal_hex": self.rgb_to_hex(va),
        }