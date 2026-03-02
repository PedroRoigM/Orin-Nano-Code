import serial
import time

def main():
    # Configuration
    port = "COM12"
    baudrate = 9600
    timeout = 1

    print(f"--- Starting Serial Reader on {port} ---")
    
    try:
        # Initialize Serial Connection
        ser = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(2)  # Wait for Arduino to reset
        
        print(f"Connected to {port} at {baudrate} baud.")
        print("Press Ctrl+C to stop.\n")

        # Main Loop: Read and Print
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    print(f"[Arduino] {line}")
            
            time.sleep(0.01)  # Small delay to reduce CPU usage

    except serial.SerialException as e:
        print(f"Error: Could not open port {port}. {e}")
    except KeyboardInterrupt:
        print("\n--- Stopping Serial Reader ---")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed.")

if __name__ == "__main__":
    main()
