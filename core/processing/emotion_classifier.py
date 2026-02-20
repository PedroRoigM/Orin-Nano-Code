from collections import deque
import numpy as np


class EmotionClassifier:
    """
    EEG-based emotion classifier for NeuroSky MindWave Mobile 2.

    Bands disponibles: delta, theta, lowAlpha, highAlpha,
                       lowBeta, highBeta, lowGamma, highGamma
    eSense (0-100):    attention, meditation

    Referencias de mappings:
      - Theta frontal  → carga cognitiva, ansiedad leve, memoria de trabajo
      - Alpha          → relajación, estado idle (relación inversa con engagement)
      - Beta           → procesamiento activo, foco, estrés
      - Gamma          → procesamiento cognitivo de alto nivel
      - Delta          → solo interpretable como baseline/ruido en sujeto despierto
    """

    SMOOTH_WINDOW = 5  # samples para moving average (a 0.5s/sample → 2.5s de contexto)

    def __init__(self, smooth_window: int = 5):
        self.smooth_window = smooth_window
        # Buffer para suavizar las emociones antes de clasificar
        self._history: dict[str, deque] = {}

    def classify_emotions(self, eeg: dict) -> dict:
        raw = self._compute_raw(eeg)
        smoothed = self._smooth(raw)
        etiqueta, valence, arousal = self._categorize_russell(smoothed)

        return {
            **smoothed,
            "valence": round(valence, 2),   # -1.0 a 1.0
            "arousal": round(arousal, 2),   # -1.0 a 1.0
            "categoria_russell": etiqueta,
        }

    # ------------------------------------------------------------------
    # Cálculo de emociones en escala 0-100
    # ------------------------------------------------------------------

    def _compute_raw(self, eeg: dict) -> dict:
        def w(*pairs):
            return int(min(100, max(0, sum(eeg.get(k, 0) * v for k, v in pairs))))
        # .get() en lugar de [] — evita KeyError silencioso

        return {
            "attention":  eeg.get("attention", 0),
            "meditation": eeg.get("meditation", 0),
            "calma":      w(("highAlpha", 0.5), ("meditation", 0.5)),
            "serenidad":  w(("theta", 0.4), ("lowAlpha", 0.4), ("meditation", 0.2)),
            "foco":       w(("attention", 0.6), ("lowBeta", 0.4)),
            "estres":     w(("theta", 0.4), ("highBeta", 0.4), ("lowGamma", 0.2)),
            "excitacion": w(("highBeta", 0.4), ("lowGamma", 0.35), ("highGamma", 0.25)),
            "felicidad":  w(("highAlpha", 0.4), ("lowBeta", 0.3), ("attention", 0.3)),
            "fatiga":     w(("delta", 0.6), ("theta", 0.4)),
        }

    # ------------------------------------------------------------------
    # Suavizado temporal
    # ------------------------------------------------------------------

    def _smooth(self, raw: dict) -> dict:
        smoothed = {}
        for key, val in raw.items():
            if key not in self._history:
                self._history[key] = deque([val] * self.smooth_window, maxlen=self.smooth_window)
            self._history[key].append(val)
            smoothed[key] = int(np.mean(self._history[key]))
        return smoothed

    # ------------------------------------------------------------------
    # Russell Circumplex: valencia × arousal
    # ------------------------------------------------------------------

    def _categorize_russell(self, emo: dict) -> tuple[str, float, float]:
        """
        Deriva valencia y arousal como dimensiones continuas.

        Valence (+): calma, felicidad, meditation
        Valence (-): estres, fatiga
        Arousal (+): excitacion, foco, estres
        Arousal (-): calma, serenidad, fatiga
        """
        # Normalizar a -1..1 desde 0..100
        def n(x): return (x - 50) / 50.0

        valence = (
            n(emo["felicidad"]) * 0.4 +
            n(emo["calma"])     * 0.3 +
            n(emo["meditation"])* 0.2 -
            n(emo["estres"])    * 0.4 -
            n(emo["fatiga"])    * 0.2
        )
        arousal = (
            n(emo["excitacion"]) * 0.4 +
            n(emo["foco"])       * 0.3 +
            n(emo["estres"])     * 0.3 -
            n(emo["calma"])      * 0.3 -
            n(emo["serenidad"])  * 0.2 -
            n(emo["fatiga"])     * 0.2
        )
        valence = float(np.clip(valence, -1, 1))
        arousal = float(np.clip(arousal, -1, 1))

        # Cuadrantes Russell
        if valence >= 0 and arousal >= 0:
            label = "Activa/Positiva"    # feliz, excitado
        elif valence >= 0 and arousal < 0:
            label = "Pasiva/Positiva"    # sereno, relajado
        elif valence < 0 and arousal >= 0:
            label = "Activa/Negativa"    # estresado, ansioso
        else:
            label = "Pasiva/Negativa"    # triste, fatigado

        return label, valence, arousal