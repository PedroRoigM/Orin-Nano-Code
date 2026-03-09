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
        # 1. LEDs (LED_1, LED_2)
        separator("1. LED Test")
        for led_id in ["LED_1", "LED_2"]:
            step(f"Testing {led_id}")
            arduino.leds._id = led_id # Manually switch for testing multiple instances
            verify_future(arduino.leds.on())
            time.sleep(0.5)
            verify_future(arduino.leds.off())
            time.sleep(0.5)
            verify_future(arduino.leds.blink())
            time.sleep(1.0)
            verify_future(arduino.leds.off())
        arduino.leds._id = "LED_1" # Reset

        # 2. Buzzers (BUZZ_1, BUZZ_2)
        separator("2. Buzzer Test")
        for buzz_id in ["BUZZ_1", "BUZZ_2"]:
            step(f"Testing {buzz_id}")
            arduino.buzzer._id = buzz_id
            verify_future(arduino.buzzer.tone(440, 200))
            time.sleep(0.3)
            verify_future(arduino.buzzer.tone(880, 200))
            time.sleep(0.3)
            verify_future(arduino.buzzer.off())

        # 3. Motors (MOT_1, MOT_2, MOT_3, MOT_4)
        separator("3. Motor Test")
        for mot_id in ["MOT_1", "MOT_2", "MOT_3", "MOT_4"]:
            step(f"Testing {mot_id}")
            arduino.tank._id = mot_id
            verify_future(arduino.tank.forward(100))
            time.sleep(0.5)
            verify_future(arduino.tank.backward(100))
            time.sleep(0.5)
            verify_future(arduino.tank.stop())

        # 4. Ultrasound (US_1, US_2)
        separator("4. Ultrasound Test")
        for us_id in ["US_1", "US_2"]:
            step(f"Testing {us_id}")
            arduino.ultrasonic._id = us_id
            # Send PING if the observer supports it (it should if mapped)
            # Otherwise we just check if readings are coming in
            print(f"  Waiting for readings from {us_id}...")
            time.sleep(1.0)
            dist = arduino.ultrasonic.distance_cm
            print(f"  Distance: {dist:.1f} cm")

        # 5. Eyes (EYE_1)
        separator("5. Eyes Test")
        step("Testing EYE_1")
        verify_future(arduino.eyes.set_color(255, 0, 0)) # Red
        time.sleep(0.5)
        verify_future(arduino.eyes.set_color(0, 255, 0)) # Green
        time.sleep(0.5)
        verify_future(arduino.eyes.set_shape("star"))
        time.sleep(1.0)
        verify_future(arduino.eyes.set_shape("circle"))
        time.sleep(0.5)
        verify_future(arduino.eyes.update(0, 0, 255)) # Blue gaze
        time.sleep(1.0)
        verify_future(arduino.eyes.set_idle())

    finally:
        arduino.stop()
        print("\nHardware test finished.")

if __name__ == "__main__":
    main()
