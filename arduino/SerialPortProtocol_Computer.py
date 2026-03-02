import serial
import time
import sys

class ArduinoInterface:
    def __init__(self, port="COM12", baudrate=9600, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # Wait for Arduino to reset
            print(f"Connected to {self.port} at {self.baudrate} baud.")
            return True
        except serial.SerialException as e:
            print(f"Error: Could not open port {self.port}. {e}")
            return False

    def send_command(self, command):
        if self.ser and self.ser.is_open:
            print(f"[Sending] {command}")
            self.ser.write((command + "\n").encode('utf-8'))
            return True
        return False

    def read_feedback(self, timeout=2):
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    return line
            time.sleep(0.1)
        return None

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial connection closed.")

def run_once_tests(port="COM12"):
    arduino = ArduinoInterface(port=port)
    if not arduino.connect():
        return

    print("\n--- Starting 'Run Once' Test Suite ---")

    # List of tests: (Command, Description)
    tests = [
        ("LED:ON", "Turning LED ON"),
        ("LED:OFF", "Turning LED OFF"),
        ("LED:BLINK", "Toggling LED (BLINK)"),
        ("BUZZ:1000,500", "Buzzer 1kHz for 500ms"),
        ("BUZZ:OFF", "Buzzer OFF"),
        ("LCD:Hello Arduino!", "LCD Text Update"),
        ("MOT:FWD,150", "Motor Forward at speed 150"),
        ("MOT:REV,150", "Motor Reverse at speed 150"),
        ("MOT:STOP,0", "Motor STOP"),
        ("US:PING", "Ultrasound Distance Check"),
    ]

    for cmd, desc in tests:
        print(f"\n[Test] {desc}")
        arduino.send_command(cmd)
        
        # Wait for feedback
        # Some commands might trigger multiple lines (like setup prints)
        # We'll just read one line expecting the feedback we just added
        feedback = arduino.read_feedback()
        if feedback:
            print(f"[Arduino Feedback] {feedback}")
        else:
            print("[Warning] No feedback received within timeout.")
        
        time.sleep(1)  # Gap between tests

    print("\n--- Test Suite Complete ---")
    arduino.close()

def main():
    port = "COM12"
    if len(sys.argv) > 1:
        port = sys.argv[1]
    
    run_once_tests(port)

if __name__ == "__main__":
    main()
