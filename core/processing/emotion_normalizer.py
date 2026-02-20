# src/processing/emotion_normalizer.py
import numpy as np
from collections import deque


class EmotionNormalizer:
    """
    Normalización adaptativa por percentil.
    
    En lugar de rangos fijos (que siempre quedan desactualizados),
    mantiene un histórico por banda y normaliza contra el percentil
    5-95 observado en sesión. Necesita ~20 samples de warm-up.
    """

    # Rangos iniciales amplios como bootstrap — se actualizan adaptativamente
    _BOOTSTRAP_RANGES = {
        'delta':    (0, 2_000_000),
        'theta':    (0, 600_000),
        'lowAlpha': (0, 300_000),
        'highAlpha':(0, 200_000),
        'lowBeta':  (0, 150_000),
        'highBeta': (0, 100_000),
        'lowGamma': (0, 50_000),
        'highGamma':(0, 50_000),
        'attention':    (0, 100),
        'meditation':   (0, 100),
    }

    HISTORY_SIZE = 120  # ~60s a 0.5s/sample

    def __init__(self):
        self._history: dict[str, deque] = {
            k: deque(maxlen=self.HISTORY_SIZE)
            for k in self._BOOTSTRAP_RANGES
        }

    def normalize(self, val: float, band: str) -> float:
        history = self._history.get(band)
        if history is None:
            return 50.0

        history.append(val)

        if len(history) < 10:
            # Warm-up: usar rangos bootstrap
            lo, hi = self._BOOTSTRAP_RANGES.get(band, (0, 100))
        else:
            # Percentil 5-95 del histórico para ignorar outliers
            arr = np.array(history)
            lo = np.percentile(arr, 5)
            hi = np.percentile(arr, 95)

        if hi <= lo:
            return 50.0

        normalized = (val - lo) / (hi - lo) * 100
        return round(float(np.clip(normalized, 0, 100)), 2)

    def normalize_all(self, eeg_data: dict) -> dict:
        return {k: self.normalize(v, k) for k, v in eeg_data.items()}