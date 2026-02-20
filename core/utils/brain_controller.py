import numpy as np
from collections import deque

class BrainController:
    def __init__(self, attention_threshold=65, meditation_threshold=60):
        self.attention_threshold = attention_threshold
        self.meditation_threshold = meditation_threshold
        self._attention_buffer = deque(maxlen=4)   # ~2s a 0.5s/sample
        self._meditation_buffer = deque(maxlen=4)

    def update(self, emotions: dict) -> dict:
        self._attention_buffer.append(emotions["attention"])
        self._meditation_buffer.append(emotions["meditation"])

        sustained_attention = np.mean(self._attention_buffer)
        sustained_meditation = np.mean(self._meditation_buffer)

        return {
            "focus_trigger": sustained_attention > self.attention_threshold,
            "calm_trigger":  sustained_meditation > self.meditation_threshold,
            "attention_level": sustained_attention,   # 0-100 continuo
            "meditation_level": sustained_meditation,
        }