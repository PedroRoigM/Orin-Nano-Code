"""
media_controller.py
-------------------
Módulo para reproducir sonidos de robot según la emoción detectada.
Uso con visión por computador (cámara).

Dependencias:
    pip install sounddevice numpy

Uso básico:
    from core.controllers.media_controller import play_emotion_sound
    play_emotion_sound("happiness")       # Elige variante aleatoria
    play_emotion_sound("anger")
    play_emotion_sound("sadness")
    play_emotion_sound("surprise")
    play_emotion_sound("fear")
    play_emotion_sound("disgust")
    play_emotion_sound("contempt")
    play_emotion_sound("neutral")
    play_emotion_sound("happiness", blocking=True)  # Bloquea hasta terminar
    play_emotion_sound("happiness", variant=2)      # Variante concreta (1, 2 o 3)
    stop_sound()                                    # Detiene cualquier sonido
"""

import numpy as np
import sounddevice as sd
import threading
import random

# ---------------------------------------------------------------------------
# Colores asociados a cada emoción
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Utilidades de síntesis — voz robótica base (sinusoide + detune + armónicos)
# ---------------------------------------------------------------------------

def _silence(d):
    return np.zeros(int(SAMPLE_RATE * d), dtype=np.float32)

def _concat(*a):
    return np.concatenate(a)

def _tone(freq, duration, volume=0.45, detune=0):
    """Tono robótico: fundamental + detune + 2º armónico."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    wave  = np.sin(2 * np.pi * freq * t) * 0.6
    wave += np.sin(2 * np.pi * (freq + detune) * t) * 0.25
    wave += np.sin(2 * np.pi * freq * 2 * t) * 0.15
    return (wave * volume).astype(np.float32)

def _env(audio, attack=0.04, release=0.12):
    """Fade in/out suave — evita clicks."""
    n = len(audio)
    env = np.ones(n)
    a, r = int(attack * n), int(release * n)
    if a > 0: env[:a] = np.linspace(0, 1, a)
    if r > 0: env[n-r:] = np.linspace(1, 0, r)
    return audio * env

def _sweep(f0, f1, duration, volume=0.4):
    """Barrido de frecuencia sinusoidal."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    phase = 2 * np.pi * np.cumsum(np.linspace(f0, f1, len(t))) / SAMPLE_RATE
    wave  = np.sin(phase) * 0.65
    wave += np.sin(phase * 2) * 0.2
    return (wave * volume).astype(np.float32)

def _wobble(freq, duration, volume=0.4, wobble_rate=8, wobble_depth=15):
    """Vibrato rápido — expresividad robótica estilo Wall-E."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq_mod = freq + wobble_depth * np.sin(2 * np.pi * wobble_rate * t)
    phase = 2 * np.pi * np.cumsum(freq_mod) / SAMPLE_RATE
    return (np.sin(phase) * volume).astype(np.float32)

def _chirp(f0, f1, duration, volume=0.42):
    """Chirp con envelope de campana — sonido expresivo de pájaro robótico."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    phase = 2 * np.pi * np.cumsum(np.linspace(f0, f1, len(t))) / SAMPLE_RATE
    env = np.sin(np.pi * t / duration)
    return (np.sin(phase) * env * volume).astype(np.float32)

def _blip(freq, duration=0.07, volume=0.45):
    """Beep corto y expresivo."""
    return _env(_tone(freq, duration, volume), attack=0.05, release=0.2)

def _stutter(freq, n=3, on=0.06, off=0.04, volume=0.4):
    """Tartamudeo robótico."""
    parts = []
    for _ in range(n):
        parts.append(_env(_tone(freq, on, volume)))
        parts.append(_silence(off))
    return _concat(*parts)

def _trill(f1, f2, n=4, duration=0.08, volume=0.4):
    """Trino robótico — alterna entre dos notas."""
    parts = []
    for i in range(n):
        f = f1 if i % 2 == 0 else f2
        parts.append(_env(_tone(f, duration, volume)))
        parts.append(_silence(0.02))
    return _concat(*parts)

def _arpeggio(freqs, duration=0.12, gap=0.06, volume=0.42):
    """Secuencia rápida de notas."""
    parts = []
    for f in freqs:
        parts.append(_blip(f, duration, volume))
        parts.append(_silence(gap))
    return _concat(*parts)

def _pulse(freq, n=4, on=0.1, off=0.08, volume=0.38):
    """Pulsos regulares y constantes."""
    parts = []
    for _ in range(n):
        parts.append(_env(_tone(freq, on, volume)))
        parts.append(_silence(off))
    return _concat(*parts)

# ---------------------------------------------------------------------------
# HAPPINESS — celebración robótica
# ---------------------------------------------------------------------------

def _happiness_v1():
    """Trino + escala ascendente rápida."""
    tr = _trill(600, 800, n=4, duration=0.07)
    sc = _arpeggio([523, 659, 784, 1047], duration=0.14)
    w  = _env(_wobble(880, 0.4, wobble_rate=12, wobble_depth=25), release=0.2)
    return _concat(tr, _silence(0.1), sc, w)

def _happiness_v2():
    """Fanfarria con chirps dobles."""
    c1 = _chirp(400, 1000, 0.14)
    c2 = _chirp(500, 1100, 0.14)
    b1 = _blip(784, 0.2)
    b2 = _blip(1047, 0.2)
    w  = _env(_wobble(1047, 0.45, wobble_rate=10, wobble_depth=18), release=0.2)
    return _concat(c1, _silence(0.04), c2, _silence(0.1), b1, _silence(0.08), b2, _silence(0.08), w)

def _happiness_v3():
    """Melodía saltarina y juguetona."""
    notes = [523, 659, 523, 784, 659, 880]
    parts = []
    for f in notes:
        parts.append(_blip(f, 0.1))
        parts.append(_silence(0.05))
    final = _env(_wobble(880, 0.38, wobble_rate=9, wobble_depth=20), release=0.18)
    return _concat(*parts, final)

# ---------------------------------------------------------------------------
# ANGER — reconoce tensión → calma descendente
# ---------------------------------------------------------------------------

def _anger_v1():
    """Pulso bajo de alerta → sweep suave descendente + wobble calmante."""
    alert = _pulse(180, n=2, on=0.12, off=0.08, volume=0.38)
    calm  = _sweep(500, 280, 0.5, volume=0.35)
    w     = _env(_wobble(330, 0.45, wobble_rate=4, wobble_depth=6), release=0.25)
    return _concat(alert, _silence(0.25), calm, _silence(0.1), w)

def _anger_v2():
    """Tono grave de reconocimiento → melodía calmante ascendente."""
    rec = _env(_tone(150, 0.2, volume=0.4, detune=4))
    c1  = _chirp(280, 520, 0.28, volume=0.37)
    b1  = _blip(440, 0.22)
    b2  = _blip(523, 0.22)
    b3  = _blip(659, 0.3)
    return _concat(rec, _silence(0.28), c1, _silence(0.08), b1, _silence(0.08), b2, _silence(0.08), b3)

def _anger_v3():
    """Stutter bajo → trino suave + chirp tranquilizador."""
    rec = _stutter(200, n=2, on=0.1, off=0.07, volume=0.37)
    tr  = _trill(380, 440, n=4, duration=0.1)
    w   = _env(_wobble(440, 0.5, wobble_rate=4, wobble_depth=7), release=0.25)
    c   = _chirp(350, 600, 0.25, volume=0.36)
    return _concat(rec, _silence(0.3), tr, _silence(0.1), c, _silence(0.08), w)

# ---------------------------------------------------------------------------
# SADNESS — reconoce con ternura → anima hacia arriba
# ---------------------------------------------------------------------------

def _sadness_v1():
    """Sweep bajito de 'oh' → escala esperanzadora."""
    oh  = _env(_sweep(380, 300, 0.35, volume=0.33))
    up  = _arpeggio([349, 440, 523, 659], duration=0.2, gap=0.08)
    w   = _env(_wobble(659, 0.45, wobble_rate=5, wobble_depth=10), release=0.22)
    return _concat(oh, _silence(0.22), up, w)

def _sadness_v2():
    """Blip bajito → trill tierno + chirp animado."""
    oh  = _blip(300, 0.2, volume=0.32)
    tr  = _trill(440, 523, n=3, duration=0.12)
    c   = _chirp(350, 750, 0.28, volume=0.38)
    b   = _blip(784, 0.3)
    return _concat(oh, _silence(0.25), tr, _silence(0.1), c, _silence(0.08), b)

def _sadness_v3():
    """Sweep bajito → pulsos animadores + nota alta final."""
    down = _env(_sweep(420, 320, 0.3, volume=0.32))
    p    = _pulse(440, n=3, on=0.14, off=0.12, volume=0.38)
    c    = _chirp(400, 800, 0.22, volume=0.38)
    b    = _env(_wobble(784, 0.4, wobble_rate=6, wobble_depth=12), release=0.2)
    return _concat(down, _silence(0.2), p, c, _silence(0.08), b)

# ---------------------------------------------------------------------------
# SURPRISE — se sorprende → tranquiliza
# ---------------------------------------------------------------------------

def _surprise_v1():
    """Chirp explosivo → stutter → baja con calma."""
    up   = _chirp(250, 1500, 0.16, volume=0.48)
    st   = _stutter(750, n=2, on=0.05, off=0.04, volume=0.4)
    down = _chirp(800, 420, 0.3, volume=0.37)
    w    = _env(_wobble(440, 0.38, wobble_rate=5, wobble_depth=8), release=0.2)
    return _concat(up, _silence(0.04), st, _silence(0.18), down, _silence(0.08), w)

def _surprise_v2():
    """Dos chirps de sorpresa → arpeggio descendente tranquilizador."""
    c1  = _chirp(300, 1200, 0.14, volume=0.46)
    c2  = _chirp(400, 1300, 0.14, volume=0.43)
    arp = _arpeggio([784, 659, 523, 440], duration=0.15, gap=0.06)
    w   = _env(_wobble(440, 0.38, wobble_rate=4, wobble_depth=7), release=0.2)
    return _concat(c1, _silence(0.05), c2, _silence(0.2), arp, w)

def _surprise_v3():
    """Trill de alarma → sweep descendente + blips calmantes."""
    tr   = _trill(900, 1100, n=3, duration=0.06)
    down = _sweep(1000, 400, 0.28, volume=0.38)
    b1   = _blip(523, 0.22)
    b2   = _blip(440, 0.28)
    return _concat(tr, _silence(0.15), down, _silence(0.1), b1, _silence(0.08), b2)

# ---------------------------------------------------------------------------
# FEAR — pulsos temblorosos → ritmo constante tranquilizador
# ---------------------------------------------------------------------------

def _fear_v1():
    """Stutter tembloroso → pulsos lentos y seguros."""
    tremble = _stutter(370, n=3, on=0.07, off=0.05, volume=0.34)
    steady  = _pulse(440, n=4, on=0.18, off=0.2, volume=0.38)
    up      = _chirp(380, 620, 0.28, volume=0.37)
    return _concat(tremble, _silence(0.3), steady, up)

def _fear_v2():
    """Blips irregulares → sweep ascendente + wobble estable."""
    b1  = _blip(360, 0.09, volume=0.33)
    b2  = _blip(380, 0.09, volume=0.33)
    b3  = _blip(350, 0.09, volume=0.33)
    sw  = _sweep(350, 580, 0.4, volume=0.36)
    w   = _env(_wobble(523, 0.5, wobble_rate=4, wobble_depth=7), release=0.22)
    fin = _blip(659, 0.3)
    return _concat(b1, _silence(0.07), b2, _silence(0.05), b3, _silence(0.3),
                   sw, _silence(0.1), w, _silence(0.08), fin)

def _fear_v3():
    """Tono bajo tembloroso → arpeggio ascendente muy suave."""
    low = _env(_wobble(250, 0.25, wobble_rate=12, wobble_depth=18), release=0.2)
    arp = _arpeggio([330, 392, 440, 523, 659], duration=0.18, gap=0.1)
    w   = _env(_wobble(523, 0.42, wobble_rate=4, wobble_depth=6), release=0.22)
    return _concat(low, _silence(0.28), arp, w)

# ---------------------------------------------------------------------------
# DISGUST — nota malestar → redirige con energía limpia y positiva
# ---------------------------------------------------------------------------

def _disgust_v1():
    """Glitch corto → chirp limpio + arpeggio positivo."""
    glitch = _env(_tone(280, 0.12, volume=0.36, detune=12))
    c      = _chirp(320, 700, 0.22, volume=0.38)
    arp    = _arpeggio([440, 523, 659], duration=0.16, gap=0.07)
    w      = _env(_wobble(659, 0.4, wobble_rate=7, wobble_depth=12), release=0.2)
    return _concat(glitch, _silence(0.22), c, _silence(0.08), arp, w)

def _disgust_v2():
    """Sweep corto hacia abajo → trill alegre que redirige."""
    down = _sweep(500, 300, 0.2, volume=0.34)
    tr   = _trill(440, 550, n=4, duration=0.1)
    b1   = _blip(523, 0.2)
    b2   = _blip(659, 0.28)
    return _concat(down, _silence(0.22), tr, _silence(0.1), b1, _silence(0.08), b2)

def _disgust_v3():
    """Stutter de malestar → blips limpios ascendentes."""
    st  = _stutter(260, n=2, on=0.08, off=0.06, volume=0.34)
    p1  = _blip(392, 0.18)
    p2  = _blip(440, 0.18)
    p3  = _blip(523, 0.18)
    c   = _chirp(400, 750, 0.25, volume=0.38)
    w   = _env(_wobble(523, 0.38, wobble_rate=6, wobble_depth=10), release=0.2)
    return _concat(st, _silence(0.25), p1, _silence(0.08), p2, _silence(0.08),
                   p3, _silence(0.1), c, _silence(0.08), w)

# ---------------------------------------------------------------------------
# CONTEMPT — nota distancia/frialdad → responde con calidez para conectar
# ---------------------------------------------------------------------------

def _contempt_v1():
    """Blip seco (distancia) → chirp + trill cálido de tercera."""
    dry = _env(_tone(320, 0.1, volume=0.37, detune=3))
    c   = _chirp(280, 560, 0.25, volume=0.38)
    tr  = _trill(494, 587, n=3, duration=0.11)  # Si-Re, tercera cálida
    w   = _env(_wobble(494, 0.45, wobble_rate=6, wobble_depth=9), release=0.22)
    return _concat(dry, _silence(0.28), c, _silence(0.1), tr, _silence(0.08), w)

def _contempt_v2():
    """Sweep sube y cae (expresa distancia) → arpeggio amigable que abre."""
    up   = _chirp(300, 600, 0.14)
    fall = _chirp(600, 350, 0.14, volume=0.35)
    arp  = _arpeggio([392, 494, 587, 698], duration=0.16, gap=0.07)  # Sol-Si-Re-Fa#
    w    = _env(_wobble(587, 0.42, wobble_rate=5, wobble_depth=10), release=0.2)
    return _concat(up, fall, _silence(0.25), arp, w)

def _contempt_v3():
    """Pulso único seco → trino cálido + nota sostenida abierta."""
    pulse = _env(_tone(300, 0.13, volume=0.38, detune=2))
    tr    = _trill(440, 554, n=4, duration=0.1)  # La-Do#, tercera mayor
    b     = _blip(587, 0.22)
    w     = _env(_wobble(659, 0.48, wobble_rate=5, wobble_depth=11), release=0.25)
    return _concat(pulse, _silence(0.3), tr, _silence(0.1), b, _silence(0.08), w)

# ---------------------------------------------------------------------------
# NEUTRAL — estado normal de operación
# ---------------------------------------------------------------------------

def _neutral_v1():
    """Secuencia de blips estándar con mini sweep."""
    b1 = _blip(660, 0.18)
    b2 = _blip(660, 0.18)
    sw = _sweep(580, 720, 0.2, volume=0.34)
    b3 = _blip(784, 0.25)
    return _concat(b1, _silence(0.1), b2, _silence(0.1), sw, _silence(0.08), b3)

def _neutral_v2():
    """Trill de operación + blip de confirmación."""
    tr = _trill(600, 700, n=3, duration=0.09)
    b1 = _blip(660, 0.18)
    w  = _env(_wobble(660, 0.3, wobble_rate=6, wobble_depth=10), release=0.18)
    b2 = _blip(784, 0.22)
    return _concat(tr, _silence(0.1), b1, _silence(0.1), w, _silence(0.08), b2)

def _neutral_v3():
    """Arpeggio de diagnóstico — como el robot escaneando."""
    arp = _arpeggio([523, 659, 784, 659], duration=0.13, gap=0.05)
    b   = _blip(660, 0.2)
    c   = _chirp(600, 720, 0.18, volume=0.34)
    b2  = _blip(784, 0.25)
    return _concat(arp, b, _silence(0.08), c, _silence(0.08), b2)

# ---------------------------------------------------------------------------
# Mapa de emociones → lista de variantes
# ---------------------------------------------------------------------------

EMOTION_SOUNDS = {
    "happiness": [_happiness_v1, _happiness_v2, _happiness_v3],
    "anger":     [_anger_v1,     _anger_v2,     _anger_v3],
    "sadness":   [_sadness_v1,   _sadness_v2,   _sadness_v3],
    "surprise":  [_surprise_v1,  _surprise_v2,  _surprise_v3],
    "fear":      [_fear_v1,      _fear_v2,      _fear_v3],
    "disgust":   [_disgust_v1,   _disgust_v2,   _disgust_v3],
    "contempt":  [_contempt_v1,  _contempt_v2,  _contempt_v3],
    "neutral":   [_neutral_v1,   _neutral_v2,   _neutral_v3],
}

# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def play_emotion_sound(emotion: str, blocking: bool = False, variant: int = None):
    """
    Reproduce el sonido correspondiente a la emoción detectada.

    Args:
        emotion:  Nombre de la emoción. No distingue mayúsculas/minúsculas.
        blocking: Si True, espera a que el sonido termine antes de continuar.
                  Si False (por defecto), reproduce en hilo aparte para no
                  bloquear el bucle de la cámara.
        variant:  Variante concreta (1, 2 o 3). Si es None, elige aleatoriamente.

    Ejemplo:
        play_emotion_sound("happiness")
        play_emotion_sound("anger", blocking=True)
        play_emotion_sound("neutral", variant=2)
    """
    emotion = emotion.lower().strip()
    if emotion not in EMOTION_SOUNDS:
        print(f"[media_controller] Emoción desconocida: '{emotion}'. "
              f"Opciones: {list(EMOTION_SOUNDS.keys())}")
        return

    variants = EMOTION_SOUNDS[emotion]
    if variant is not None:
        idx = max(0, min(variant - 1, len(variants) - 1))
        sound_fn = variants[idx]
    else:
        sound_fn = random.choice(variants)

    audio = sound_fn()

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
    """Para cualquier sonido que esté reproduciéndose."""
    sd.stop()


# ---------------------------------------------------------------------------
# Demo / test rápido
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import time

    print("Probando sonidos de robot por emoción (3 variantes cada una)...\n")
    for emotion in EMOTION_SOUNDS:
        for i in range(1, 4):
            print(f"  → {emotion} variante {i}")
            play_emotion_sound(emotion, blocking=True, variant=i)
            time.sleep(0.25)
        print()
    print("¡Listo!")