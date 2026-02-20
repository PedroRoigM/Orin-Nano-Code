import serial
from enum import IntEnum

class BufferValues(IntEnum):
        BUFFER_START = 64  # '@'
        BUFFER_END = 13    # CR (Carriage Return)

class Port:
    def __init__(self, port_name: str='/dev/ttyACM0'):
        self.port_name = port_name.strip()
        # Configuramos pero no abrimos (como autoOpen: false)
        self.connection = serial.Serial()
        self.connection.port = self.port_name
        self.connection.baudrate = 9600
        self.connection.bytesize = serial.EIGHTBITS
        self.connection.stopbits = serial.STOPBITS_ONE
        self.connection.parity = serial.PARITY_NONE
        self.connection.timeout = 1

    def send_data(self, data: list[int]) -> list[int]:
        """
        Envía un array de números enmarcados por START y END.
        Equivalente al async sendData de tu código Node.
        """
        # Crear el buffer (como Buffer.from([...]))
        payload = [64] + data + [13]
        print(payload)
        buffer_to_send = bytes(payload)

        try:
            # 1. Abrir puerto
            if not self.connection.is_open:
                self.connection.open()

            # 2. Escribir datos
            self.connection.write(buffer_to_send)

            # 3. Drenar (flush en Python asegura que se envíe todo el buffer)
            self.connection.flush()

            return list(buffer_to_send)

        except Exception as e:
            print(f"ERROR: {e}")
            raise
        finally:
            # 4. Cerrar puerto
            if self.connection.is_open:
                self.connection.close()