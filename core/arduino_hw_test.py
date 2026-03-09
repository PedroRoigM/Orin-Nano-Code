import time
import sys
import serial.tools.list_ports
from concurrent.futures import Future, wait, FIRST_EXCEPTION

from controllers.arduino_controller import ArduinoController

# ── Configuration ─────────────────────────────────────────────────────────────
BAUD = 115200  # New firmware uses 115200 usually, or what is defined in the script
ULTRASONIC_THRESHOLD_CM = 15.0

def detect_arduino_port():
    candidates = []
    for p in serial.tools.list_ports.comports():
        dev = p.device or ""
        desc = (p.description or "").lower()
        if ("arduino" in desc or "mega" in desc or "usbmodem" in dev or "ttyACM" in dev or "usbserial" in dev):
            candidates.append(dev)
    return candidates[0] if candidates else None

# ── Helpers ───────────────────────────────────────────────────────────────────
def separator(label: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {label.upper()}")
    print('═' * 60)

def step(msg: str) -> None:
    print(f"\n[STEP] {msg}")

def verify_future(future: Future, timeout: float = 2.0):
    try:
        if future is None:
            print("  ! No future returned (command might have been skipped)")
            return
        res = future.result(timeout=timeout)
        print(f"  ✓ ACK received: {res}")
    except Exception as e:
        print(f"  ✗ FAILED: {e}")

# ── Main Test ─────────────────────────────────────────────────────────────────
def main():
    port = detect_arduino_port()
    if not port:
        print("Error: No Arduino found. Please connect the board.")
        sys.exit(1)

    print(f"Connecting to Arduino on {port} @ {BAUD} baud...")
    arduino = ArduinoController(port, BAUD, ultrasonic_threshold_cm=ULTRASONIC_THRESHOLD_CM, verbose=True)
    arduino.start()
    time.sleep(2.0)

    try:
        # 1. LEDs
        separator("1. LED Test")
        for led_ctrl, led_id in [(arduino.led_1, "LED_1"), (arduino.led_2, "LED_2")]:
            step(f"Testing {led_id}")
            verify_future(led_ctrl.on())
            time.sleep(0.5)
            verify_future(led_ctrl.off())
            time.sleep(0.5)
            verify_future(led_ctrl.blink())
            time.sleep(1.0)
            verify_future(led_ctrl.off())

        # 2. Buzzers
        separator("2. Buzzer Test")
        for buzz_ctrl, buzz_id in [(arduino.buzzer_1, "BUZZ_1"), (arduino.buzzer_2, "BUZZ_2")]:
            step(f"Testing {buzz_id}")
            verify_future(buzz_ctrl.tone(440, 200))
            time.sleep(0.3)
            verify_future(buzz_ctrl.tone(880, 200))
            time.sleep(0.3)
            verify_future(buzz_ctrl.off())

        # 3. Motors
        separator("3. Motor Test")
        for mot_ctrl, mot_id in [(arduino.motor_1, "MOT_1"), (arduino.motor_2, "MOT_2"), (arduino.motor_3, "MOT_3"), (arduino.motor_4, "MOT_4")]:
            step(f"Testing {mot_id}")
            verify_future(mot_ctrl.forward(100))
            time.sleep(0.5)
            verify_future(mot_ctrl.backward(100))
            time.sleep(0.5)
            verify_future(mot_ctrl.stop())

        # 4. Ultrasound
        separator("4. Ultrasound Test")
        for us_ctrl, us_id in [(arduino.ultrasound_1, "US_1"), (arduino.ultrasound_2, "US_2")]:
            step(f"Testing {us_id}")
            print(f"  Waiting for readings from {us_id}...")
            time.sleep(1.0)
            dist = us_ctrl.distance_cm
            print(f"  Distance: {dist:.1f} cm")

        # 5. Eyes
        separator("5. Eyes Test")
        for eye_ctrl, eye_id in [(arduino.eyes_1, "EYE_1"), (arduino.eyes_2, "EYE_2")]:
            step(f"Testing {eye_id}")
            verify_future(eye_ctrl.set_color(255, 0, 0)) # Red
            time.sleep(0.5)
            verify_future(eye_ctrl.set_color(0, 255, 0)) # Green
            time.sleep(0.5)
            verify_future(eye_ctrl.set_shape("star"))
            time.sleep(1.0)
            verify_future(eye_ctrl.set_shape("circle"))
            time.sleep(0.5)
            verify_future(eye_ctrl.update(0, 0, 255)) # Blue gaze
            time.sleep(1.0)
            verify_future(eye_ctrl.set_idle())

    finally:
        arduino.stop()
        print("\nHardware test finished.")

if __name__ == "__main__":
    main()
