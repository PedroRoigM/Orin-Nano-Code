from port import Port
from commandValues import CommandValues
from nodeValues import NodeValues

class HoloController:
	def __init__(self, port_name=None):
		self.port = Port(port_name)

	def _isParameterValid(self, parameter:int):
		if not (1 <= parameter <= 4):
			raise ValueError(f"Parameter value not valid")
	def _isNodeValid(self, node):
		if node not in [NodeValues.HOLO_FIRST, NodeValues.HOLO_SECOND, NodeValues.HOLO_THIRD]:
			raise ValueError(f"Node value not valid")
	def _isColorValid(self, color):
		if not (0 <= color <= 255):
			raise ValueError(f"Color value not valid")
	def _isProgramValid(self, program):
		if not (1 <= program <= 6):
			raise ValueError(f"Program value not valid")

	def moveHoloServo(self, node, all, parameter):
		try:
			self._isParameterValid(parameter)
			self._isNodeValid(node)
			self.port.send_data([CommandValues.MOVE_HOLO_SERVO, node, all, parameter])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def changeHoloRGBColor(self, node, all, colors:list):
		try:
			self._isNodeValid(node)
			[self._isColorValid(color) for color in colors]

			self.port.send_data([CommandValues.SET_HOLO_COLOR, node, all] + colors)
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def changeHoloProgram(self, node, all, program):
		try:
			self._isNodeValid(node)
			self._isProgramValid(program)

			self.port.send_data([CommandValues.SET_HOLO_COLOR, node, all, program])
		except Exception as e:
			print(f"ERROR: {e}")
			return

def main():
	holoController = HoloController('/dev/cu.usbmodem594D0064841')
	for i in range(10):
		holoController.changeHoloRGBColor(3, 1, [0, 255, 0, 0])

if __name__ == '__main__':
	main()
