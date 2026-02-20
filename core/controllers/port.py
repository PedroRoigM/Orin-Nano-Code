import serial
import serial.tools.list_ports
from enum import IntEnum
from time import sleep
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
		payload = [BufferValues.BUFFER_START] + data + [BufferValues.BUFFER_END]
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

	@staticmethod
	def list_serial_ports():
		"""Equivalente a SerialPort.list()"""
		return serial.tools.list_ports.comports()

# --- Ejemplo de uso ---
if __name__ == "__main__":
	#print(serial.tools.list_ports.comports())

	# Cambia esto por tu puerto detectado: 
	p = Port('/dev/cu.usbmodem594D0064841')

	try:
		# Enviamos los mismos bytes del ejemplo anterior
		#raw_payload = [84, 6, 20, 52]
		#raw_payload = [76, 9, 5, 255, 0, 0, 0]
		for i in range(0, 256): 
			raw_payload = [76, 9, 4, 0, 255, i, 0]
			written = p.send_data(raw_payload)
			raw_payload = [76, 5, 1, 0, 255, i, 0]
			written = p.send_data(raw_payload)
			raw_payload = [84, 6,3, i]
			written = p.send_data(raw_payload)
			
			sleep(0.01)
		raw_payload = [87, 8, 0, 49, 58]
		written = p.send_data(raw_payload)
		print(f"Bytes enviados: {written}")
	except Exception as e:
		print(f"Falló el envío: {e}")
