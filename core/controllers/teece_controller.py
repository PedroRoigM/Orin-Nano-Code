from controllers.port import Port
from enum import IntEnum
from controllers.nodeValues import NodeValues
from controllers.commandValues import CommandValues

class DisplayValues(IntEnum):
	ALL_TEECES = 1
	TOP_FLD = 2
	BOTTOM_FLD = 3
	REAR_FLD = 4

	FRONT_PSI = 5
	REAR_PSI = 6

	MAGIC_LIGHTS = 7

class ProgramMode(IntEnum):
	OFF = 49
	RANDOM = 50
	ALARM = 51
	ERROR = 52
	LEIA = 53
	STARWARS = 54
	IMPERIAL = 55
	BARCODE = 56

class TeeceController:
	def __init__(self, port=None, port_name='/dev/ttyAMC1'):
		self.port = port if port is not None else Port(port_name)
	def _isColorValid(self, color:int):
		if not (0 <= color <= 255):
			raise ValueError(f"Color value not in valid range [0, 255]")

	def _isProgramValid(self, program:int):
		if not (49 <= program <= 56):
			raise ValueError(f"Program not valid, range [49, 56]")
	def _isTextValid(self, text:list):
		if not (1 <= len(text) <= 30):
			raise ValueError(f"Text len is not valid")

	def setColor(self, display, colors:list):
		try:
			[self._isColorValid(color) for color in colors]
			self.port.send_data([CommandValues.SET_TEECE_COLOR, NodeValues.TEECE_COLOR, display, colors[0], colors[1], colors[2], colors[3]])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def setProgram(self, display, program):
		try:
			self._isProgramValid(program)
			self.port.send_data([CommandValues.SET_PROGRAM, NodeValues.TEECE_COMMAND_TEXT, display, program])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def _transformTextToASCII(self, text: list) -> list:
		ascii_list = [ord(item) for item in text]
		return ascii_list
	def setText(self, display, text:list) -> None:
		try:
			self._isTextValid(text)
			command = [CommandValues.SET_TEECE_TEXT, NodeValues.TEECE_COMMAND_TEXT, display] + self._transformTextToASCII(text)
			self.port.send_data(command)
		except Exception as e:
			print(f"ERROR: {e}")

def main():
	teeceController = TeeceController()
	teeceController.setText(20, ['H', 'O', 'L', 'A'])
#	teeceController.setProgram(20, 52)
	#teeceController.setColor(20, 255, 0,0, 0)
if __name__ == "__main__":
	main()
