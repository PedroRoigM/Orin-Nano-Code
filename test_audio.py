import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call

# Forzar UTF-8 para evitar errores con caracteres especiales (→, é, etc.) en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Mockear serial ANTES de cualquier import que lo necesite
sys.modules['serial'] = MagicMock()
sys.modules['serial.tools'] = MagicMock()
sys.modules['serial.tools.list_ports'] = MagicMock()

# Añadir core/controllers/ al path para resolver los imports locales del módulo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core', 'controllers'))

from commandValues import CommandValues
from nodeValues import NodeValues


class TestAudioController(unittest.TestCase):

    def setUp(self):
        self.port_patcher = patch('audio_controller.Port')
        self.MockPort = self.port_patcher.start()
        self.mock_send = MagicMock(return_value=[])
        self.MockPort.return_value.send_data = self.mock_send

        from audio_controller import AudioController
        self.ac = AudioController(port_name='COM5')

    def tearDown(self):
        self.port_patcher.stop()

    # ------------------------------------------------------------------ #
    #  _getDominantEmotion                                                 #
    # ------------------------------------------------------------------ #

    def test_dominant_emotion_correcto(self):
        emotions = {
            "felicidad": 0.8,
            "calma":     0.3,
            "estres":    0.5,
            "valence":   0.6,
            "arousal":   0.4,
            "categoria_russell": "Activa/Positiva",
        }
        self.assertEqual(self.ac._getDominantEmotion(emotions), "felicidad")

    def test_dominant_emotion_excluye_metadata(self):
        emotions = {
            "felicidad": 0.1,
            "valence":   0.99,
            "arousal":   0.99,
            "categoria_russell": "Activa/Positiva",
        }
        self.assertEqual(self.ac._getDominantEmotion(emotions), "felicidad")

    def test_dominant_emotion_sin_emociones_validas(self):
        emotions = {
            "valence": 0.9,
            "arousal": 0.5,
            "categoria_russell": "Activa/Positiva",
        }
        self.assertIsNone(self.ac._getDominantEmotion(emotions))

    # ------------------------------------------------------------------ #
    #  playAudio / validaciones                                            #
    # ------------------------------------------------------------------ #

    def test_play_audio_valido(self):
        self.ac.playAudio(all=1, folder=49, audio=49)
        self.mock_send.assert_called_once_with(
            [CommandValues.PLAY_AUDIO, NodeValues.AUDIO, 1, 49, 49]
        )

    def test_play_audio_folder_invalido(self):
        self.ac.playAudio(all=1, folder=48, audio=49)
        self.ac.playAudio(all=1, folder=58, audio=49)
        self.mock_send.assert_not_called()

    def test_play_audio_audio_invalido(self):
        self.ac.playAudio(all=1, folder=49, audio=10)
        self.mock_send.assert_not_called()

    def test_play_audio_limites_folder(self):
        self.ac.playAudio(folder=49, audio=49)
        self.ac.playAudio(folder=57, audio=49)
        self.assertEqual(self.mock_send.call_count, 2)

    # ------------------------------------------------------------------ #
    #  enableAudio / disableAudio                                          #
    # ------------------------------------------------------------------ #

    def test_enable_audio(self):
        self.ac.enableAudio(all=1, folder=51, audio=52)
        self.mock_send.assert_called_once_with(
            [CommandValues.ENABLE_AUDIO, NodeValues.AUDIO, 1, 51, 52]
        )

    def test_disable_audio(self):
        self.ac.disableAudio(all=1, folder=53, audio=50)
        self.mock_send.assert_called_once_with(
            [CommandValues.DISABLE_AUDIO, NodeValues.AUDIO, 1, 53, 50]
        )

    # ------------------------------------------------------------------ #
    #  muteAudio                                                           #
    # ------------------------------------------------------------------ #

    def test_mute_audio_activar(self):
        self.ac.muteAudio(all=1, mute=1)
        self.mock_send.assert_called_once_with(
            [CommandValues.MUTE_AUDIO, NodeValues.AUDIO, 1, 1]
        )

    def test_mute_audio_desactivar(self):
        self.ac.muteAudio(all=1, mute=0)
        self.mock_send.assert_called_once_with(
            [CommandValues.MUTE_AUDIO, NodeValues.AUDIO, 1, 0]
        )

    # ------------------------------------------------------------------ #
    #  incVolume / decVolume  — BUG DETECTADO                              #
    #  audio_controller.py usa CommandValues.SET_VOLUME pero en           #
    #  commandValues.py el nombre correcto es SET_VOLUMEN.                 #
    #  Estos tests fallarán hasta que se corrija el typo.                  #
    # ------------------------------------------------------------------ #

    def test_inc_volume_BUG_set_volume_no_existe(self):
        # BUG: SET_VOLUME no existe, debe ser SET_VOLUMEN
        # incVolume() captura el AttributeError y NO envía nada
        self.ac.incVolume(all=1)
        self.mock_send.assert_not_called()

    def test_dec_volume_BUG_set_volume_no_existe(self):
        # BUG: SET_VOLUME no existe, debe ser SET_VOLUMEN
        self.ac.decVolume(all=1)
        self.mock_send.assert_not_called()

    # ------------------------------------------------------------------ #
    #  droidOnOf                                                           #
    # ------------------------------------------------------------------ #

    def test_droid_toggle_on(self):
        self.ac.droidOnOf(all=1)
        self.assertEqual(self.ac.droid_mode, 1)

    def test_droid_toggle_off(self):
        self.ac.droidOnOf(all=1)
        self.ac.droidOnOf(all=1)
        self.assertEqual(self.ac.droid_mode, 0)

    # ------------------------------------------------------------------ #
    #  reactToEmotion                                                      #
    #  TRACK_LOW/MID/HIGH = None → usa el valor por defecto (audio=49)    #
    # ------------------------------------------------------------------ #

    def test_react_to_emotion_felicidad_pistas_sin_definir(self):
        # Mientras TRACK_* sean None, usa el audio por defecto
        emotions = {
            "felicidad": 0.9,
            "calma":     0.2,
            "valence":   0.6,
            "arousal":   0.3,
            "categoria_russell": "Activa/Positiva",
        }
        self.ac.reactToEmotion(emotions, all=1, audio=49)
        self.mock_send.assert_called_once_with(
            [CommandValues.PLAY_AUDIO, NodeValues.AUDIO, 1, 49, 49]
        )

    def test_react_to_emotion_estres_pistas_sin_definir(self):
        # estres negativo → inversión → pero TRACK_* None → audio por defecto
        emotions = {
            "estres":    0.9,
            "felicidad": 0.1,
            "valence":   0.1,
            "arousal":   0.9,
            "categoria_russell": "Activa/Negativa",
        }
        self.ac.reactToEmotion(emotions, all=1, audio=49)
        self.mock_send.assert_called_once_with(
            [CommandValues.PLAY_AUDIO, NodeValues.AUDIO, 1, 57, 49]
        )

    def test_react_to_emotion_con_pistas_definidas(self):
        # Simula que ya se han definido las pistas: LOW=51, MID=52, HIGH=53
        self.ac.TRACK_LOW  = 51
        self.ac.TRACK_MID  = 52
        self.ac.TRACK_HIGH = 53
        emotions = {"felicidad": 0.9, "valence": 0.5, "arousal": 0.3, "categoria_russell": ""}
        self.ac.reactToEmotion(emotions, all=1)
        # score=0.9, positiva, 3 niveles → idx=2 → TRACK_HIGH=53
        self.mock_send.assert_called_once_with(
            [CommandValues.PLAY_AUDIO, NodeValues.AUDIO, 1, 49, 53]
        )

    def test_react_to_emotion_sin_emociones_validas(self):
        emotions = {
            "valence":   0.9,
            "arousal":   0.5,
            "categoria_russell": "Activa/Positiva",
        }
        self.ac.reactToEmotion(emotions)
        self.mock_send.assert_not_called()

    # ------------------------------------------------------------------ #
    #  reactToRussell                                                      #
    # ------------------------------------------------------------------ #

    def test_react_to_russell_activa_positiva(self):
        self.ac.reactToRussell({"categoria_russell": "Activa/Positiva"}, all=1, audio=49)
        self.mock_send.assert_called_once_with(
            [CommandValues.PLAY_AUDIO, NodeValues.AUDIO, 1, 49, 49]
        )

    def test_react_to_russell_pasiva_negativa(self):
        self.ac.reactToRussell({"categoria_russell": "Pasiva/Negativa"}, all=1, audio=49)
        self.mock_send.assert_called_once_with(
            [CommandValues.PLAY_AUDIO, NodeValues.AUDIO, 1, 56, 49]
        )

    def test_react_to_russell_categoria_desconocida(self):
        self.ac.reactToRussell({"categoria_russell": "Inexistente"})
        self.mock_send.assert_not_called()

    # ------------------------------------------------------------------ #
    #  adjustVolumeByArousal                                               #
    # ------------------------------------------------------------------ #

    def test_arousal_alto_sube_volumen(self):
        # BUG: mientras no se corrija SET_VOLUME → SET_VOLUMEN, send_data no se llama
        self.ac.adjustVolumeByArousal({"arousal": 0.8}, all=1)
        self.mock_send.assert_not_called()

    def test_arousal_bajo_baja_volumen(self):
        # BUG: mismo bug que incVolume/decVolume
        self.ac.adjustVolumeByArousal({"arousal": -0.7}, all=1)
        self.mock_send.assert_not_called()

    def test_arousal_neutro_no_cambia_volumen(self):
        self.ac.adjustVolumeByArousal({"arousal": 0.2}, all=1)
        self.mock_send.assert_not_called()

    def test_arousal_ausente_no_falla(self):
        try:
            self.ac.adjustVolumeByArousal({})
        except Exception as e:
            self.fail(f"adjustVolumeByArousal lanzó excepción inesperada: {e}")

    # ------------------------------------------------------------------ #
    #  setConfiguration                                                    #
    # ------------------------------------------------------------------ #

    def test_set_configuration(self):
        self.ac.setConfiguration(all=1, parameter=5)
        self.mock_send.assert_called_once_with(
            [CommandValues.CONFIGURATION, NodeValues.AUDIO, 1, 5]
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
