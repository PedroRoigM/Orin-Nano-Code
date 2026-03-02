from controllers.port import Port
from enum import IntEnum
from controllers.commandValues import CommandValues
from controllers.nodeValues import NodeValues

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

	# Emociones negativas: a mayor intensidad, R2 reacciona más suave (para calmar al niño)
	EMOTION_POLARITY = {
		"felicidad":  "positive",
		"excitacion": "positive",
		"foco":       "positive",
		"attention":  "positive",
		"calma":      "positive",
		"serenidad":  "positive",
		"meditation": "positive",
		"fatiga":     "negative",
		"estres":     "negative",
	}

	# TODO: rellenar con los números de pista reales cuando se organicen las carpetas
	TRACK_LOW  = None  # [num] pista suave
	TRACK_MID  = None  # [num] pista media
	TRACK_HIGH = None  # [num] pista enérgica

	_EXCLUDE = {"valence", "arousal", "categoria_russell"}

	def __init__(self, port=None, port_name='/dev/ttyACM1'):
		self.port = port if port is not None else Port(port_name)
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

	def _scoreToAudio(self, score: float, levels: int = 3) -> int:
		"""Mapea un score (0.0-1.0) a una pista: TRACK_LOW, TRACK_MID o TRACK_HIGH."""
		tracks = [self.TRACK_LOW, self.TRACK_MID, self.TRACK_HIGH][:levels]
		idx = min(int(score * levels), levels - 1)
		return tracks[idx]

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

	def reactToEmotion(self, emotions: dict, all: int = 1, levels: int = 3, audio: int = 49):
		dominant = self._getDominantEmotion(emotions)
		if dominant is None:
			return
		score = emotions.get(dominant, 0.0)
		folder = self.EMOTION_FOLDER_MAP[dominant]
		# Emociones negativas: invertir la intensidad para que R2 sea más suave
		if self.EMOTION_POLARITY.get(dominant) == "negative":
			score = 1.0 - score
		track = self._scoreToAudio(score, levels=levels)
		# Si las pistas aún no están definidas, usa el valor por defecto
		if track is None:
			track = audio
		print(f"[AUDIO] {dominant} (score={score:.2f}) → folder {folder}, pista {track}")
		self.playAudio(all=all, folder=folder, audio=track)

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

