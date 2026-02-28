"""
media_controller.py
-------------------
Módulo para reproducir sonidos de robot según la emoción detectada.
Uso con visión por computador (cámara).
Dependencias:
    pip install sounddevice numpy
Uso básico:
    from core.controllers.media_controller import play_emotion_sound
    play_emotion_sound("happiness")
    Importar:
    from core.controllers.media_controller import play_emotion_sound
    play_emotion_sound("happiness")  # Reproduce sonido de felicidad
    play_emotion_sound("anger")      # Reproduce sonido de ira 
    play_emotion_sound("sadness")   # Reproduce sonido de tristeza
    play_emotion_sound("surprise")  # Reproduce sonido de sorpresa
    play_emotion_sound("fear")      # Reproduce sonido de miedo
    play_emotion_sound("disgust")   # Reproduce sonido de asco
    play_emotion_sound("contempt")  # Reproduce sonido de desprecio
    play_emotion_sound("neutral")   # Reproduce sonido neutral
    play_emotion_sound("happiness", blocking=True)  # Bloquea hasta terminar
    stop_sound()  # Detiene cualquier sonido en reproducción
"""
import numpy as np
import sounddevice as sd
import threading

EMOTION_COLORS = {
    "happiness": (0, 255, 0),
    "anger":     (0, 0, 255),
    "sadness":   (255, 0, 0),
    "surprise":  (0, 255, 255),
    "fear":      (128, 0, 128),
    "disgust":   (0, 128, 0),
    "contempt":  (128, 128, 0),
    "neutral":   (200, 200, 200),
}
SAMPLE_RATE = 44100  # Hz

def _generate_tone(freq, duration, volume=0.4, wave="sine"):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    if wave == "sine":
        audio = np.sin(2 * np.pi * freq * t)
    elif wave == "square":
        audio = np.sign(np.sin(2 * np.pi * freq * t))
    elif wave == "sawtooth":
        audio = 2 * (t * freq - np.floor(0.5 + t * freq))
    elif wave == "noise":
        audio = np.random.uniform(-1, 1, len(t))
    else:
        audio = np.sin(2 * np.pi * freq * t)
    return (audio * volume).astype(np.float32)

def _apply_envelope(audio, attack=0.01, decay=0.05, sustain=0.7, release=0.1):
    n = len(audio)
    envelope = np.ones(n)
    a = int(attack * n)
    d = int(decay * n)
    r = int(release * n)
    envelope[:a] = np.linspace(0, 1, a)
    envelope[a:a+d] = np.linspace(1, sustain, d)
    envelope[a+d:n-r] = sustain
    envelope[n-r:] = np.linspace(sustain, 0, r)
    return audio * envelope

def _sweep(freq_start, freq_end, duration, volume=0.4, wave="sine"):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq_t = np.linspace(freq_start, freq_end, len(t))
    phase = 2 * np.pi * np.cumsum(freq_t) / SAMPLE_RATE
    if wave == "sine":
        audio = np.sin(phase)
    elif wave == "square":
        audio = np.sign(np.sin(phase))
    else:
        audio = np.sin(phase)
    return (audio * volume).astype(np.float32)

def _concat(*arrays):
    return np.concatenate(arrays)

def _silence(duration):
    return np.zeros(int(SAMPLE_RATE * duration), dtype=np.float32)

def _sound_happiness():
    s1 = _apply_envelope(_generate_tone(523, 0.12))
    s2 = _apply_envelope(_generate_tone(659, 0.12))
    s3 = _apply_envelope(_generate_tone(784, 0.12))
    s4 = _apply_envelope(_generate_tone(1047, 0.25))
    return _concat(s1, _silence(0.03), s2, _silence(0.03), s3, _silence(0.03), s4)

def _sound_anger():
    s1 = _apply_envelope(_generate_tone(80, 0.15, volume=0.6, wave="square"))
    s2 = _apply_envelope(_generate_tone(100, 0.15, volume=0.6, wave="square"))
    s3 = _apply_envelope(_generate_tone(60, 0.3, volume=0.7, wave="square"))
    buzz = _generate_tone(150, 0.1, volume=0.5, wave="square")
    return _concat(s1, buzz, s2, buzz, s3)

def _sound_sadness():
    sweep_down = _apply_envelope(_sweep(600, 200, 0.8, volume=0.35), release=0.3)
    s1 = _apply_envelope(_generate_tone(220, 0.4, volume=0.3))
    return _concat(sweep_down, _silence(0.1), s1)

def _sound_surprise():
    sweep_up = _sweep(300, 1200, 0.18, volume=0.5)
    beep = _apply_envelope(_generate_tone(1200, 0.15, volume=0.45))
    return _concat(sweep_up, beep)

def _sound_fear():
    pulses = []
    freqs = [400, 380, 420, 360, 440, 350]
    for i, f in enumerate(freqs):
        dur = 0.07 + (i % 2) * 0.03
        pulses.append(_apply_envelope(_generate_tone(f, dur, volume=0.4)))
        pulses.append(_silence(0.04 + (i % 3) * 0.02))
    noise = _generate_tone(0, 0.1, wave="noise") * 0.15
    return _concat(*pulses, noise)

def _sound_disgust():
    s1 = _generate_tone(311, 0.3, volume=0.35, wave="sawtooth")
    s2 = _generate_tone(466, 0.3, volume=0.35, wave="sawtooth")
    combined = _apply_envelope((s1 + s2) * 0.5, release=0.2)
    glitch = _generate_tone(233, 0.1, volume=0.3, wave="square")
    return _concat(combined, glitch)

def _sound_contempt():
    beep = _generate_tone(180, 0.08, volume=0.5, wave="square")
    t = np.linspace(0, 1, len(beep))
    beep = beep * np.exp(-t * 15)
    silence = _silence(0.05)
    short = _generate_tone(160, 0.05, volume=0.3, wave="square")
    return _concat(beep, silence, short)

def _sound_neutral():
    return _apply_envelope(_generate_tone(800, 0.12, volume=0.35))

EMOTION_SOUNDS = {
    "happiness": _sound_happiness,
    "anger":     _sound_anger,
    "sadness":   _sound_sadness,
    "surprise":  _sound_surprise,
    "fear":      _sound_fear,
    "disgust":   _sound_disgust,
    "contempt":  _sound_contempt,
    "neutral":   _sound_neutral,
}

def play_emotion_sound(emotion: str, blocking: bool = False):
    emotion = emotion.lower().strip()
    if emotion not in EMOTION_SOUNDS:
        print(f"[media_controller] Emoción desconocida: '{emotion}'. "
              f"Opciones: {list(EMOTION_SOUNDS.keys())}")
        return
    audio = EMOTION_SOUNDS[emotion]()
    if blocking:
        sd.play(audio, SAMPLE_RATE)
        sd.wait()
    else:
        def _play():
            sd.play(audio, SAMPLE_RATE)
            sd.wait()
        t = threading.Thread(target=_play, daemon=True)
        t.start()

def stop_sound():
    sd.stop()

if __name__ == "__main__":
    import time
    print("Probando sonidos de robot por emoción...\n")
    for emotion in EMOTION_SOUNDS:
        print(f"  → {emotion}")
        play_emotion_sound(emotion, blocking=True)
        time.sleep(0.3)
    print("\n¡Listo!")
