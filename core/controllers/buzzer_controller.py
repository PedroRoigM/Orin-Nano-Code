"""
buzzer_controller.py
====================
Controla el buzzer/zumbador conectado al Arduino (nuevo firmware ArduinoBoardFirmware).

Protocolo texto (newline-terminado):
  BUZZ:<freq>,<duration_ms>\n   → reproduce un tono a <freq> Hz durante <duration_ms> ms
  BUZZ:OFF\n                    → detiene el tono activo

El Coordinator del Arduino enruta al BuzzerController registrado bajo "BUZZ".
El Arduino usa tone(pin, freq, duration) internamente.

Respuesta del Arduino (ignorada en Python):
  BUZZ_1:PLAYING:<freq>,<duration_ms>
  BUZZ_1:OFF

Integración con emociones:
  buzzer.react_to_emotion("happiness")   → pitido positivo
  buzzer.react_to_emotion("anger")       → tono de alerta
  buzzer.react_to_obstacle(dist_cm)      → beep de proximidad
"""


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v)))


class BuzzerController:

    # Parámetros de tono por emoción (freq_hz, duration_ms)
    _EMOTION_TONES: dict[str, tuple[int, int]] = {
        "neutral":   (440,  100),
        "happiness": (880,  150),
        "surprise":  (660,  200),
        "sadness":   (220,  500),
        "anger":     (150,  400),
        "disgust":   (180,  300),
        "fear":      (800,   80),   # beep corto y agudo
        "contempt":  (300,  250),
    }

    def __init__(self, port, controller_id: str = "BUZZ_1", verbose: bool = False):
        self._port    = port
        self._id      = controller_id
        self._verbose = verbose

    # ── API principal ────────────────────────────────────────────────────────

    def tone(self, freq: int, duration_ms: int) -> None:
        """
        Reproduce un tono.
        freq:        Hz (20-20000)
        duration_ms: milisegundos (1-30000)
        """
        f = _clamp(freq,        20,    20_000)
        d = _clamp(duration_ms,  1,    30_000)
        self._send(f"SOUND:{f},{d}")

    def off(self) -> None:
        """Detiene el tono activo."""
        self._send("OFF")

    # ── Métodos de conveniencia ───────────────────────────────────────────────

    def beep(self, freq: int = 1000, duration_ms: int = 200) -> None:
        """Pitido corto genérico."""
        self.tone(freq, duration_ms)

    def react_to_emotion(self, emotion: str) -> None:
        """Emite el tono asociado a la emoción detectada."""
        freq, duration = self._EMOTION_TONES.get(emotion, (440, 100))
        self.tone(freq, duration)

    def react_to_obstacle(self, distance_cm: float, threshold_cm: float = 10.0) -> None:
        """
        Emite un beep proporcional a la proximidad del obstáculo.
        Cuanto más cerca, más agudo y corto.
        No emite nada si la distancia supera el umbral.
        """
        if distance_cm < 0 or distance_cm >= threshold_cm:
            return
        # Mapear distancia (0..threshold) → frecuencia (2000..500 Hz)
        ratio = max(0.0, min(1.0, distance_cm / threshold_cm))
        freq  = int(500 + (1 - ratio) * 1500)   # cerca=2000 Hz, lejos=500 Hz
        dur   = int(50  + ratio        * 150)    # cerca=50 ms, lejos=200 ms
        self.tone(freq, dur)

    def startup_chime(self) -> None:
        """Melodía de arranque (tres tonos ascendentes)."""
        import time
        for freq in (440, 660, 880):
            self.tone(freq, 120)
            time.sleep(0.14)

    # ── Interno ──────────────────────────────────────────────────────────────

    def _send(self, command: str) -> None:
        try:
            # Nuevo protocolo: {BASE_ID}:{SPECIFIC_ID}:{COMMAND}
            line = f"BUZZ:{self._id}:{command}"
            if self._verbose:
                print(f"[BUZZ] → {line}")
            self._port.send_line(line)
        except Exception as e:
            print(f"[BUZZ] ERROR: {e}")

    # ── Unit Test ────────────────────────────────────────────────────────────

    def test_interface(self) -> bool:
        """
        Prueba la interfaz enviando comandos básicos.
        Retorna True si no hubo excepciones.
        """
        print(f"--- Testing BuzzerController ({self._id}) ---")
        try:
            self.off()
            self.beep()
            self.tone(440, 100)
            self.react_to_emotion("happiness")
            print("[BUZZ] Test interface OK")
            return True
        except Exception as e:
            print(f"[BUZZ] Test interface FAILED: {e}")
            return False
