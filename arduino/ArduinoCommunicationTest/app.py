import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import serial
import serial.tools.list_ports
import threading
import time
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'arduino_secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

serial_port = None
read_thread = None
running = False

def read_from_serial():
    global serial_port, running
    while running:
        if serial_port and serial_port.is_open:
            try:
                if serial_port.in_waiting > 0:
                    # Read all available bytes
                    data = serial_port.read(serial_port.in_waiting)
                    text = data.decode('utf-8', errors='replace')
                    
                    # Log to server console for debugging
                    print(f"Serial Read: {repr(text)}")
                    
                    # Split by lines in case multiple messages arrived
                    lines = text.splitlines()
                    for line in lines:
                        line = line.strip()
                        if line:
                            socketio.emit('serial_data', {'data': line})
            except Exception as e:
                print(f"Serial Error: {e}")
                socketio.emit('serial_error', {'error': str(e)})
                running = False
        time.sleep(0.05) # Small sleep to avoid CPU hogging

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ports', methods=['GET'])
def get_ports():
    ports = serial.tools.list_ports.comports()
    return jsonify([port.device for port in ports])

@app.route('/connect', methods=['POST'])
def connect():
    global serial_port, read_thread, running
    data = request.json
    port_name = data.get('port')
    baudrate = data.get('baudrate', 115200)

    try:
        if serial_port and serial_port.is_open:
            serial_port.close()
        
        serial_port = serial.Serial(port_name, baudrate, timeout=1)
        running = True
        read_thread = threading.Thread(target=read_from_serial, daemon=True)
        read_thread.start()
        return jsonify({"status": "connected", "port": port_name})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/disconnect', methods=['POST'])
def disconnect():
    global serial_port, running
    running = False
    if serial_port and serial_port.is_open:
        serial_port.close()
    return jsonify({"status": "disconnected"})

@app.route('/send', methods=['POST'])
def send_command():
    global serial_port
    data = request.json
    command = data.get('command')
    
    if serial_port and serial_port.is_open:
        try:
            serial_port.write((command + '\n').encode('utf-8'))
            return jsonify({"status": "sent", "command": command})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400
    else:
        return jsonify({"status": "error", "message": "Serial port not connected"}), 400

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
