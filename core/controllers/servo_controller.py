from enum import IntEnum
from controllers.port import Port
from controllers.commandValues import CommandValues


class NodeValues(IntEnum):
	SERVO = 1

class ServoController:
	def __init__(self, port=None, port_name='/dev/ttyACM0'):
		self.port = port if port is not None else Port(port_name)

	def _isPositionValid(self, pos: int):
		if not (0 <= pos <= 255):
			raise ValueError("Servo position not in range (0, 255)")

	def _isServoNumberValid(self, nServo: int):
		if not (0 <= nServo <= 47):
			raise ValueError("Servo number not in range (0, 47)")

	def moveServoSlow(self, all, nServo: int, pos: int):
		try:
			self._isPositionValid(pos)
			self._isServoNumberValid(nServo)
			self.port.send_data([CommandValues.MOVE_SERVO_SLOW, NodeValues.SERVO, all, nServo, pos])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def moveServoFast(self, all, nServo, pos):
		try:
			self._isPositionValid(pos)
			self._isServoNumberValid(nServo)
			self.port.send_data([CommandValues.MOVE_SERVO_FAST, NodeValues.SERVO, all, nServo, pos])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def setServoInitialPosition(self, all, nServo, pos):
		try:
			self._isPositionValid(pos)
			self._isServoNumberValid(nServo)
			self.port.send_data([CommandValues.SET_SERVO_INIT_POS, NodeValues.SERVO, all, nServo, pos])
		except Exception as e:
			print(f"ERROR: {e}")

	def moveServoToInitialPosition(self, all, nServo, pos):
		try:
			self._isPositionValid(pos)
			self._isServoNumberValid(nServo)
			self.port.send_data([CommandValues.MOVE_SERVO_TO_INIT_POS, NodeValues.SERVO, all, nServo, pos])
		except Exception as e:
			print(f"ERROR: {e}")

	def setServoSecuence(self, all, posHigh, posLow):
		try:
			self._isPositionValid(posHigh)
			self._isPositionValid(posLow)
			self.port.send_data([CommandValues.SET_SERVO_SECUENCE, NodeValues.SERVO, all, posHigh, posLow])
		except Exception as e:
			print(f"ERROR: {e}")

	def playServoSecuence(self, all):
		try:
			self.port.send_data([CommandValues.PLAY_SERVO_SECUENCE, NodeValues.SERVO, all])
		except Exception as e:
			print(f"Error: {e}")

	def stopServoSecuence(self, all):
		try:
			self.port.send_data([CommandValues.STOP_SERVO_SECUENCE, NodeValues.SERVO, all])
		except Exception as e:
			print(f"ERROR: {e}")

	def scapeServoSecuecne(self, all):
		try:
			self.port.send_data([CommandValues.SCAPE_SERVO_SECUENCE, NodeValues.SERVO, all])
		except Exception as e:
			print(f"ERROR: {e}")

	def setAllServosPosition(self, all, positions: list):
		try:
			[self._isPositionValid(position) for position in positions]
			command = [CommandValues.SET_PROGRAM, NodeValues.SERVO, all] + positions
			self.port.send_data(command)
		except Exception as e:
			print(f"ERROR: {e}")

def main():
	servoController = ServoController()
	servoController.moveServoFast(1, 0, 127)

#	servoController.setServoSecuence(1, 10, 200)
#	servoController.playServoSecuence(1)

if __name__ == '__main__':
	main()
