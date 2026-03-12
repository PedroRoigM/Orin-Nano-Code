import serial
import time
import sys

PORT = "/dev/cu.usbmodem1101"   # Linux: /dev/ttyUSB0 o /dev/ttyACM0 | macOS: /dev/cu.usbmodem... | Windows: COM3
BAUD = 9600

def send_angle(ser, servo_id: int, angle: int):
    """Envía un ángulo a un servo (1 o 2), rango 0-180."""
    angle = max(0, min(180, angle))
    cmd = f"S{servo_id}:{angle}\n"
    ser.write(cmd.encode())
    time.sleep(0.05)  # pequeña pausa para que Arduino procese

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2)  # espera reset del Arduino tras conexión serial
        print(f"Conectado a {PORT}")
    except serial.SerialException as e:
        print(f"Error al abrir puerto: {e}")
        sys.exit(1)

    try:
        # Ejemplo: sweep de 0 a 180 en ambos servos
        for angle in range(1, 180, 10):
            send_angle(ser, 1, angle)
            send_angle(ser, 2, 180 - angle)  # servo 2 inverso
            print(f"S1={angle}°  S2={180 - angle}°")
            time.sleep(0.1)

        # Volver al centro
        send_angle(ser, 1, 90)
        send_angle(ser, 2, 90)

    finally:
        ser.close()
        print("Puerto cerrado.")

if __name__ == "__main__":
    main()