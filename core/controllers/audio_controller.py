from port import Port
from enum import IntEnum
from commandValues import CommandValues
from nodeValues import NodeValues

class AudioController:

	# Cada emoción mapeada a una carpeta de audio (folders 49-57)
	EMOTION_FOLDER_MAP = {
		"felicidad":  49,
		"excitacion": 50,
		"foco":       51,
		"attention":  52,
		"calma":      53,
		"serenidad":  54,
		"meditation": 55,
		"fatiga":     56,
		"estres":     57,
	}

	# Carpeta por categoría Russell (cuadrante del circunflejo)
	RUSSELL_FOLDER_MAP = {
		"Activa/Positiva": 49,  # felicidad / excitación
		"Pasiva/Positiva": 53,  # calma / serenidad
		"Activa/Negativa": 57,  # estrés
		"Pasiva/Negativa": 56,  # fatiga
	}

	_EXCLUDE = {"valence", "arousal", "categoria_russell"}

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

	def _getDominantEmotion(self, emotions: dict):
		scores = {
			k: v for k, v in emotions.items()
			if k not in self._EXCLUDE
			and k in self.EMOTION_FOLDER_MAP
			and isinstance(v, (int, float))
		}
		if not scores:
			return None
		return max(scores, key=scores.get)

	def reactToEmotion(self, emotions: dict, all: int = 1, audio: int = 49):
		dominant = self._getDominantEmotion(emotions)
		if dominant is None:
			return
		folder = self.EMOTION_FOLDER_MAP[dominant]
		print(f"[AUDIO] Emoción dominante: {dominant} → folder {folder}")
		self.playAudio(all=all, folder=folder, audio=audio)

	def reactToRussell(self, emotions: dict, all: int = 1, audio: int = 49):
		category = emotions.get("categoria_russell", "")
		folder = self.RUSSELL_FOLDER_MAP.get(category)
		if folder is None:
			return
		print(f"[AUDIO] Russell: {category} → folder {folder}")
		self.playAudio(all=all, folder=folder, audio=audio)

	def adjustVolumeByArousal(self, emotions: dict, all: int = 1):
		arousal = emotions.get("arousal", 0.0)
		if arousal > 0.4:
			print(f"[AUDIO] Arousal alto ({arousal:.2f}) → subiendo volumen")
			self.incVolume(all=all)
		elif arousal < -0.4:
			print(f"[AUDIO] Arousal bajo ({arousal:.2f}) → bajando volumen")
			self.decVolume(all=all)

def main():
	audioController = AudioController()
	audioController.enableAudio(folder=49, audio=49)
	audioController.playAudio(folder=49, audio=49)
	#		audioController.muteAudio(1, 1)


if __name__ == "__main__":
	main()

