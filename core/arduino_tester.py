"""
Arduino component tester.

Tests: LCD · LED · Tank · Ultrasonic

Adjust PORT and BAUD before running.
"""
import time
from controllers.arduino_controller import ArduinoController

# ── Configuration ─────────────────────────────────────────────────────────────
PORT  = "/dev/ttys011"   # change to your actual port (e.g. /dev/ttyUSB0, COM3)
BAUD  = 9600
ULTRASONIC_THRESHOLD_CM = 10.0


# ── Helpers ───────────────────────────────────────────────────────────────────
def separator(label: str) -> None:
    print(f"\n{'═' * 50}")
    print(f"  {label}")
    print('═' * 50)

def step(msg: str, pause: float = 0.5) -> None:
    print(f"  → {msg}")
    time.sleep(pause)

def ok(msg: str = "") -> None:
    print(f"  ✓ {msg}" if msg else "  ✓")


# ── Init ──────────────────────────────────────────────────────────────────────
print(f"\nConnecting to Arduino on {PORT} @ {BAUD} baud …")
arduino = ArduinoController(PORT, BAUD, ultrasonic_threshold_cm=ULTRASONIC_THRESHOLD_CM)
arduino.start()
time.sleep(1.0)   # let Arduino reset and ultrasonic thread warm up


# ── 1. Ultrasonic ─────────────────────────────────────────────────────────────
separator("1 · ULTRASONIC SENSOR — live monitor (5 s)")
print("  Monitoring distance readings for 5 seconds …")
print("  (Place your hand in front of / behind the robot to test blocking)\n")

deadline = time.time() + 5.0
while time.time() < deadline:
    f  = arduino.ultrasonic.front_cm
    b  = arduino.ultrasonic.back_cm
    ff = f"{'BLOCKED' if arduino.ultrasonic.is_front_blocked else 'clear  ':7s}"
    bb = f"{'BLOCKED' if arduino.ultrasonic.is_back_blocked  else 'clear  ':7s}"
    front_str = f"{f:6.1f} cm" if f >= 0 else "  no data"
    back_str  = f"{b:6.1f} cm" if b >= 0 else "  no data"
    print(f"  front: {front_str}  [{ff}]   back: {back_str}  [{bb}]", end="\r")
    time.sleep(0.15)

print()  # newline after \r loop
print()
print(f"  Final state:")
print(f"    is_front_blocked : {arduino.ultrasonic.is_front_blocked}")
print(f"    is_back_blocked  : {arduino.ultrasonic.is_back_blocked}")
print(f"    is_blocked       : {arduino.ultrasonic.is_blocked}")
print(f"    can_move_forward : {arduino.can_move_forward}")
print(f"    can_move_backward: {arduino.can_move_backward}")
print(f"    can_turn         : {arduino.can_turn}")
ok("Ultrasonic test done")


# ── 2. LED ────────────────────────────────────────────────────────────────────
separator("2 · LED CONTROLLER")

step("set_color — RED  (255, 0, 0)")
arduino.leds.set_color(255, 0, 0)
time.sleep(0.5)

step("set_color — GREEN  (0, 255, 0)")
arduino.leds.set_color(0, 255, 0)
time.sleep(0.5)

step("set_color — BLUE  (0, 0, 255)")
arduino.leds.set_color(0, 0, 255)
time.sleep(0.5)

step("set_color — YELLOW  (255, 255, 0)")
arduino.leds.set_color(255, 255, 0)
time.sleep(0.5)

step("set_color — CYAN  (0, 255, 255)")
arduino.leds.set_color(0, 255, 255)
time.sleep(0.5)

step("set_color — WHITE  (255, 255, 255)")
arduino.leds.set_color(255, 255, 255)
time.sleep(0.5)

step("set_brightness — 50%  (128)")
arduino.leds.set_brightness(128)
time.sleep(0.5)

step("set_brightness — 100%  (255)")
arduino.leds.set_brightness(255)
time.sleep(0.4)

step("set_pattern — blink  (2)")
arduino.leds.set_pattern(2)
time.sleep(1.5)

step("set_pattern — breathing  (3)")
arduino.leds.set_pattern(3)
time.sleep(1.5)

step("set_pattern — rainbow  (4)")
arduino.leds.set_pattern(4)
time.sleep(1.5)

step("set_pattern — solid  (1)")
arduino.leds.set_pattern(1)
time.sleep(0.4)

step("off()")
arduino.leds.off()
time.sleep(0.4)
ok("LED test done")


# ── 3. LCD ────────────────────────────────────────────────────────────────────
separator("3 · LCD CONTROLLER")

step("clear()")
arduino.lcd.clear()
time.sleep(0.4)

step('display_text("Hola Mundo!",  line=0)')
arduino.lcd.display_text("Hola Mundo!", line=0)
time.sleep(0.5)

step('display_text("Test OK",  line=1)')
arduino.lcd.display_text("Test OK", line=1)
time.sleep(0.8)

step('display_text("Col offset",  line=0, col=5)')
arduino.lcd.display_text("Col offset", line=0, col=5)
time.sleep(0.8)

step('display_two_lines("Arduino", "Funcionando")')
arduino.lcd.display_two_lines("Arduino", "Funcionando")
time.sleep(1.0)

step("clear()")
arduino.lcd.clear()
time.sleep(0.4)
ok("LCD test done")


# ── 4. Tank ───────────────────────────────────────────────────────────────────
separator("4 · TANK CONTROLLER")
print("  (Robot may move — keep it on a safe surface)\n")

step("forward(50) — 0.6 s")
arduino.tank.forward(50)
time.sleep(0.6)

step("stop()")
arduino.tank.stop()
time.sleep(0.3)

step("backward(50) — 0.6 s")
arduino.tank.backward(50)
time.sleep(0.6)

step("stop()")
arduino.tank.stop()
time.sleep(0.3)

step("turn_left(45) — 0.5 s")
arduino.tank.turn_left(45)
time.sleep(0.5)

step("stop()")
arduino.tank.stop()
time.sleep(0.3)

step("turn_right(45) — 0.5 s")
arduino.tank.turn_right(45)
time.sleep(0.5)

step("stop()")
arduino.tank.stop()
time.sleep(0.3)

step("forward(100) full speed — 0.4 s")
arduino.tank.forward(100)
time.sleep(0.4)

step("stop()")
arduino.tank.stop()
time.sleep(0.3)
ok("Tank test done")


# ── Cleanup ───────────────────────────────────────────────────────────────────
separator("Cleanup")
arduino.stop()
print("\nAll tests complete.\n")
