from port import Port
from enum import IntEnum
from commandValues import CommandValues
from nodeValues import NodeValues

class AudioController:
	def __init__(self, port_name='/dev/ttyACM1'):
		self.port = Port(port_name)
		self.droid_mode = 0

	def _isFolderValid(self, folder: int):
		if not (49 <= folder <= 57):
			raise ValueError(f"Folder {folder} is not valid")

	def _isAudioValid(self, audio: int):
		if not (49 <= audio <= 255):
			raise ValueError(f"Audio {audio} is not valid")

	def playAudio(self, all= 1, folder = 49, audio = 49):
		try:
			self._isFolderValid(folder)
			self._isAudioValid(audio)
			self.port.send_data([CommandValues.PLAY_AUDIO, NodeValues.AUDIO, all, folder, audio])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def droidOnOf(self, all = 1):
		try:
			self.droid_mode = 0 if self.droid_mode else 1
			self.port.send_data([CommandValues.DROID, NodeValues.AUDIO, all, self.droid_mode])
		except Exception as e:
			print("ERROR: {e}")
			return

	def enableAudio(self, all = 1, folder = 49, audio = 49):
		try:
			self._isFolderValid(folder)
			self._isAudioValid(audio)
			self.port.send_data([CommandValues.ENABLE_AUDIO, NodeValues.AUDIO, all, folder, audio])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def disableAudio(self, all = 1, folder = 49, audio = 49):
		try:
			self._isFolderValid(folder)
			self._isAudioValid(audio)
			self.port.send_data([CommandValues.DISABLE_AUDIO, NodeValues.AUDIO, all, folder, audio])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def muteAudio(self, all = 1, mute = 0):
		try:
			self.port.send_data([CommandValues.MUTE_AUDIO, NodeValues.AUDIO, all, mute])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def incVolume(self, all = 1):
		try:
			self.port.send_data([CommandValues.SET_VOLUME, NodeValues.AUDIO, all, 1])
		except Exception as e:
			print(f"ERROR: {e}")
			return

	def decVolume(self, all = 1):
		try:
			self.port.send_data([CommandValues.SET_VOLUME, NodeValues.AUDIO, all, 0])
		except Exception as e:
			print(f"ERROR: {e}")
			return
	def setConfiguration(self, all = 1, parameter = 0):
		try:
			self.port.send_data([CommandValues.CONFIGURATION, NodeValues.AUDIO, all, parameter])
		except Exception as e:
			print(f"ERROR: {e}")
			return
def main():
	audioController = AudioController()
	audioController.enableAudio(folder=49, audio=49)
	audioController.playAudio(folder=49, audio=49)
	#		audioController.muteAudio(1, 1)


if __name__ == "__main__":
	main()

