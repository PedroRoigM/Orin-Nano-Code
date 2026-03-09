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


from concurrent.futures import Future



class BuzzerController:

    def __init__(self, port, controller_id: str = "BUZZ_1", verbose: bool = False):
        self._port    = port
        self._id      = controller_id
        self._verbose = verbose

    # ── API principal ────────────────────────────────────────────────────────

    def tone(self, freq: int, duration_ms: int) -> Future:
        """
        Reproduce un tono.
        freq:        Hz (20-20000)
        duration_ms: milisegundos (1-30000)
        """
        f = self._clamp(freq,        20,    20_000)
        d = self._clamp(duration_ms,  1,    30_000)
        return self._send(f"SOUND:{f},{d}")

    def off(self) -> Future:
        """Detiene el tono activo."""
        return self._send("OFF")

    # ── Métodos de conveniencia ───────────────────────────────────────────────

    def beep(self, freq: int = 1000, duration_ms: int = 200) -> Future:
        """Pitido corto genérico."""
        return self.tone(freq, duration_ms)

    def startup_chime(self) -> list[Future]:
        """Melodía de arranque (tres tonos ascendentes)."""
        import time
        futures = []
        for freq in (440, 660, 880):
            futures.append(self.tone(freq, 120))
            time.sleep(0.14)
        return futures
    
    def _clamp(self, v: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, int(v)))


    # ── Interno ──────────────────────────────────────────────────────────────

    def _send(self, command: str) -> Future:
        # Nuevo protocolo: {BASE_ID}:{SPECIFIC_ID}:{COMMAND}
        line = f"BUZZ:{self._id}:{command}"
        if self._verbose:
            print(f"[BUZZ] → {line}")
        return self._port.send_line(line)

    # ── Unit Test ────────────────────────────────────────────────────────────

    def test_interface(self) -> bool:
        """
        Prueba la interfaz enviando comandos básicos.
        Retorna True si no hubo excepciones (las promesas pueden no estar resueltas).
        """
        print(f"--- Testing BuzzerController ({self._id}) ---")
        try:
            self.off().result(timeout=1.0)
            self.beep().result(timeout=1.0)
            self.tone(440, 100).result(timeout=1.0)
            print("[BUZZ] Test interface OK (ACKs received)")
            return True
        except Exception as e:
            print(f"[BUZZ] Test interface FAILED or TIMEOUT: {e}")
            return False
