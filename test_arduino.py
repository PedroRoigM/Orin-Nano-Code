"""
test_arduino.py
===============
Prueba manual de todos los componentes Arduino.
Ejecutar desde la raíz del repositorio:

    cd /home/jetson/prueba
    python3 test_arduino.py

Cada componente se prueba por orden con una pausa entre ellos.
Pulsa Ctrl+C en cualquier momento para detener.
"""

import sys
import time

sys.path.insert(0, "core")

from controllers.arduino_controller import ArduinoController

PORT = "/dev/ttyACM0"
BAUD = 115200

def pause(msg: str, seconds: float = 2.0):
    print(f"\n>>> {msg}")
    time.sleep(seconds)

print("=" * 50)
print("  TEST ARDUINO — todos los componentes")
print("=" * 50)

arduino = ArduinoController(PORT, BAUD)
arduino.start()
print()

# ── 1. LEDs ───────────────────────────────────────────────────────────────────
pause("LED — ON", 1)
arduino.leds.on()
time.sleep(2)

pause("LED — BLINK", 1)
arduino.leds.blink()
time.sleep(2)

pause("LED — COLOR rojo (255, 0, 0)", 1)
arduino.leds.set_color(255, 0, 0)
time.sleep(2)

pause("LED — COLOR verde (0, 255, 0)", 1)
arduino.leds.set_color(0, 255, 0)
time.sleep(2)

pause("LED — COLOR azul (0, 0, 255)", 1)
arduino.leds.set_color(0, 0, 255)
time.sleep(2)

pause("LED — OFF", 1)
arduino.leds.off()
time.sleep(1)

# ── 2. Buzzer ─────────────────────────────────────────────────────────────────
pause("BUZZER — startup chime", 1)
arduino.buzzer.startup_chime()
time.sleep(2)

pause("BUZZER — tono 440 Hz (La)", 1)
arduino.buzzer.beep(440, 500)
time.sleep(1)

pause("BUZZER — tono 880 Hz (La agudo)", 1)
arduino.buzzer.beep(880, 500)
time.sleep(1)

pause("BUZZER — OFF", 1)
arduino.buzzer.off()
time.sleep(1)

# ── 3. Ojos GC9A01 ───────────────────────────────────────────────────────────
pause("OJOS — ON (wake up)", 1)
arduino.eyes.on()
time.sleep(2)

pause("OJOS — FILL azul oscuro", 1)
arduino.eyes.fill(0, 0, 100)
time.sleep(2)

pause("OJOS — DRAW neutral (iris blanco cálido, fondo negro)", 1)
arduino.eyes_1._last_draw_key = None   # forzar envío
arduino.eyes_2._last_draw_key = None
arduino.eyes.draw("neutral", 200, 200, 180, 0, 0, 0)
time.sleep(2)

pause("OJOS — DRAW happy (iris verde)", 1)
arduino.eyes_1._last_draw_key = None
arduino.eyes_2._last_draw_key = None
arduino.eyes.draw("happy", 100, 220, 80, 0, 0, 0)
time.sleep(2)

pause("OJOS — DRAW sad (iris naranja)", 1)
arduino.eyes_1._last_draw_key = None
arduino.eyes_2._last_draw_key = None
arduino.eyes.draw("sad", 255, 165, 50, 0, 0, 0)
time.sleep(2)

pause("OJOS — MOVE izquierda (-80, 0)", 1)
arduino.eyes_1._last_move_t = 0
arduino.eyes_2._last_move_t = 0
arduino.eyes.move(-80, 0)
time.sleep(1.5)

pause("OJOS — MOVE derecha (80, 0)", 1)
arduino.eyes_1._last_move_t = 0
arduino.eyes_2._last_move_t = 0
arduino.eyes.move(80, 0)
time.sleep(1.5)

pause("OJOS — MOVE centro (0, 0)", 1)
arduino.eyes_1._last_move_t = 0
arduino.eyes_2._last_move_t = 0
arduino.eyes.move(0, 0)
time.sleep(1.5)

pause("OJOS — OFF", 1)
arduino.eyes.off()
time.sleep(1)

# ── 4. Servos cuello (NECK) ───────────────────────────────────────────────────
pause("NECK — centro (90, 90)", 1)
arduino._port.send_line("NECK:NECK_1:MOVE:90,90")
time.sleep(1.5)

pause("NECK — girar izquierda (70, 90)", 1)
arduino._port.send_line("NECK:NECK_1:MOVE:70,90")
time.sleep(1.5)

pause("NECK — girar derecha (110, 90)", 1)
arduino._port.send_line("NECK:NECK_1:MOVE:110,90")
time.sleep(1.5)

pause("NECK — mirar arriba (90, 80)", 1)
arduino._port.send_line("NECK:NECK_1:MOVE:90,80")
time.sleep(1.5)

pause("NECK — mirar abajo (90, 100)", 1)
arduino._port.send_line("NECK:NECK_1:MOVE:90,100")
time.sleep(1.5)

pause("NECK — volver al centro (90, 90)", 1)
arduino._port.send_line("NECK:NECK_1:MOVE:90,90")
time.sleep(1.5)

# ── Fin ───────────────────────────────────────────────────────────────────────
print()
print("=" * 50)
print("  TEST COMPLETADO")
print("=" * 50)
arduino.stop()
