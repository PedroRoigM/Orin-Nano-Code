"""
test_eyes_neck.py
=================
Prueba manual de ojos (GC9A01) y servos de cuello (pan/tilt).
Ejecutar desde la raíz del repositorio:

    python3 test_eyes_neck.py

Pulsa Ctrl+C para detener en cualquier momento.
"""

import sys
import time

sys.path.insert(0, "core")

from controllers.arduino_controller import ArduinoController

PORT = "/dev/cu.usbmodem1101"
BAUD = 115200

def pause(msg: str, seconds: float = 1.5):
    print(f"\n>>> {msg}")
    time.sleep(seconds)

print("=" * 50)
print("  TEST OJOS + SERVOS")
print("=" * 50)

arduino = ArduinoController(PORT, BAUD)
arduino.start()
print()

# ── OJOS ──────────────────────────────────────────────────────────────────────

pause("OJOS — ON (wake up)", 0.5)
arduino.eyes.on()
time.sleep(1)

pause("OJOS — DRAW neutral (iris blanco cálido)", 0.5)
arduino.eyes_1._last_draw_key = None
arduino.eyes_2._last_draw_key = None
arduino.eyes.draw("neutral", 200, 200, 180, 0, 0, 0)
time.sleep(2)

pause("OJOS — DRAW happy (iris verde)", 0.5)
arduino.eyes_1._last_draw_key = None
arduino.eyes_2._last_draw_key = None
arduino.eyes.draw("happy", 100, 220, 80, 0, 0, 0)
time.sleep(2)

pause("OJOS — DRAW sad (iris naranja)", 0.5)
arduino.eyes_1._last_draw_key = None
arduino.eyes_2._last_draw_key = None
arduino.eyes.draw("sad", 255, 165, 50, 0, 0, 0)
time.sleep(2)

pause("OJOS — MOVE izquierda (-80, 0)", 0.5)
arduino.eyes_1._last_move_t = 0
arduino.eyes_2._last_move_t = 0
arduino.eyes.move(-80, 0)
time.sleep(1.5)

pause("OJOS — MOVE derecha (80, 0)", 0.5)
arduino.eyes_1._last_move_t = 0
arduino.eyes_2._last_move_t = 0
arduino.eyes.move(80, 0)
time.sleep(1.5)

pause("OJOS — MOVE arriba (0, -80)", 0.5)
arduino.eyes_1._last_move_t = 0
arduino.eyes_2._last_move_t = 0
arduino.eyes.move(0, -80)
time.sleep(1.5)

pause("OJOS — MOVE abajo (0, 80)", 0.5)
arduino.eyes_1._last_move_t = 0
arduino.eyes_2._last_move_t = 0
arduino.eyes.move(0, 80)
time.sleep(1.5)

pause("OJOS — MOVE centro (0, 0)", 0.5)
arduino.eyes_1._last_move_t = 0
arduino.eyes_2._last_move_t = 0
arduino.eyes.move(0, 0)
time.sleep(1.5)

# ── SERVOS CUELLO ─────────────────────────────────────────────────────────────

pause("NECK — centro (90, 90)", 0.5)
arduino._port.send_line("NECK:NECK_1:MOVE:90,90")
time.sleep(1.5)

pause("NECK — girar izquierda (70, 90)", 0.5)
arduino._port.send_line("NECK:NECK_1:MOVE:70,90")
time.sleep(1.5)

pause("NECK — girar derecha (110, 90)", 0.5)
arduino._port.send_line("NECK:NECK_1:MOVE:110,90")
time.sleep(1.5)

pause("NECK — mirar arriba (90, 80)", 0.5)
arduino._port.send_line("NECK:NECK_1:MOVE:90,80")
time.sleep(1.5)

pause("NECK — mirar abajo (90, 100)", 0.5)
arduino._port.send_line("NECK:NECK_1:MOVE:90,100")
time.sleep(1.5)

pause("NECK — volver al centro (90, 90)", 0.5)
arduino._port.send_line("NECK:NECK_1:MOVE:90,90")
time.sleep(1.5)

# ── Fin ───────────────────────────────────────────────────────────────────────
print()
print("=" * 50)
print("  TEST COMPLETADO")
print("=" * 50)
arduino.stop()
