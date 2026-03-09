"""
emotion_manager.py
==================
Centraliza la lógica de comportamiento y emociones del robot.
Despega esta lógica de los controladores de hardware (LED, Buzzer, etc.)
y actúa como un orquestador.
"""

from typing import Optional
from concurrent.futures import Future

# Intentar importar las definiciones de comportamiento
try:
    # Se espera que BEHAVIOR viva en core/controllers/companion_behavior.py o similar
    from .companion_behavior import BEHAVIOR
except ImportError:
    BEHAVIOR = {
        "neutral": {
            "eyes_rgb": (200, 200, 180),
            "led_rgb":  (50, 50, 50),
            "buzzer":   (440, 100),
            "lcd":      "Hello!"
        },
        "happiness": {
            "eyes_rgb": (255, 255, 0),
            "led_rgb":  (0, 255, 0),
            "buzzer":   (880, 150),
            "lcd":      "Happy! :)"
        }
        # ... resto de emociones se pueden añadir aquí
    }

class EmotionManager:
    """
    Orquestador de alto nivel para el estado emocional del robot.
    """

    def __init__(self, arduino):
        """
        arduino: instancia de ArduinoController que contiene los sub-controladores.
        """
        self._arduino = arduino
        self._current_emotion = "neutral"

    def apply_emotion(self, emotion: str, confidence: float = 1.0) -> list[Future]:
        """
        Aplica una emoción coordinando todos los actuadores.
        Retorna una lista de Futures (promesas de ejecución).
        """
        self._current_emotion = emotion
        futures = []

        cfg = BEHAVIOR.get(emotion, BEHAVIOR.get("neutral", {}))

        # 1. Ojos (Color + Mirada centrada por defecto)
        eye_rgb = cfg.get("eyes_rgb")
        if eye_rgb:
            # Los ojos suelen tener su propio ciclo de update en el loop principal,
            # pero aquí forzamos el color base.
            futures.append(self._arduino.eyes.set_color(*eye_rgb))

        # 2. LEDs
        led_rgb = cfg.get("led_rgb")
        if led_rgb:
            futures.append(self._arduino.leds.set_color(*led_rgb))

        # 3. Buzzer (Reacción sonora)
        buzz_cfg = cfg.get("buzzer") # (freq, dur)
        if buzz_cfg:
            futures.append(self._arduino.buzzer.tone(*buzz_cfg))

        # 4. LCD
        msg = cfg.get("lcd")
        if msg:
            futures.append(self._arduino.lcd.display_text(f"{msg} ({confidence:.0%})"))

        return futures

    def flash_alert(self) -> list[Future]:
        """Comportamiento de alerta (LED rojo, pitido)."""
        futures = []
        futures.append(self._arduino.leds.set_color(255, 0, 0))
        futures.append(self._arduino.leds.set_brightness(255))
        futures.append(self._arduino.buzzer.beep(1000, 500))
        return futures

    def react_to_obstacle(self, distance_cm: float, threshold_cm: float = 10.0) -> Optional[Future]:
        """
        Lógica de reacción a proximidad.
        """
        if 0 < distance_cm < threshold_cm:
            # Cuanto más cerca, más agudo
            ratio = max(0.0, min(1.0, distance_cm / threshold_cm))
            freq  = int(500 + (1 - ratio) * 1500)
            dur   = 100
            return self._arduino.buzzer.tone(freq, dur)
        return None
