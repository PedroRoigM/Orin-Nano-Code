import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Crear mocks antes de importar
sys.modules['commandValues'] = MagicMock()
sys.modules['nodeValues'] = MagicMock()

# Configurar NodeValues mock
sys.modules['nodeValues'].NodeValues = MagicMock()
sys.modules['nodeValues'].NodeValues.AUDIO = 2

from audio_controller import AudioController


@pytest.fixture
def mock_port_for_audio():
    """Mock del Port para audio controller"""
    with patch('audio_controller.Port') as mock:
        port_instance = MagicMock()
        mock.return_value = port_instance
        yield port_instance


@pytest.fixture
def audio_controller(mock_port_for_audio):
    """Instancia de AudioController con Port mockeado"""
    return AudioController()


class TestAudioControllerInit:
    """Tests para inicialización"""
    
    def test_init_default_port(self, mock_port_for_audio):
        controller = AudioController()
        assert controller.droid_mode == 0
    
    def test_init_custom_port(self):
        with patch('audio_controller.Port') as mock:
            controller = AudioController('/dev/ttyUSB0')
            mock.assert_called_once_with('/dev/ttyUSB0')


class TestAudioValidation:
    """Tests para métodos de validación"""
    
    def test_is_folder_valid_in_range(self, audio_controller):
        # No debería lanzar excepción
        audio_controller._isFolderValid(49)
        audio_controller._isFolderValid(53)
        audio_controller._isFolderValid(57)
    
    def test_is_folder_valid_below_range(self, audio_controller):
        with pytest.raises(ValueError, match="Folder .* is not valid"):
            audio_controller._isFolderValid(48)
    
    def test_is_folder_valid_above_range(self, audio_controller):
        with pytest.raises(ValueError, match="Folder .* is not valid"):
            audio_controller._isFolderValid(58)
    
    def test_is_audio_valid_in_range(self, audio_controller):
        audio_controller._isAudioValid(49)
        audio_controller._isAudioValid(150)
        audio_controller._isAudioValid(255)
    
    def test_is_audio_valid_below_range(self, audio_controller):
        with pytest.raises(ValueError, match="Audio .* is not valid"):
            audio_controller._isAudioValid(48)
    
    def test_is_audio_valid_above_range(self, audio_controller):
        with pytest.raises(ValueError, match="Audio .* is not valid"):
            audio_controller._isAudioValid(256)


class TestPlayAudio:
    """Tests para playAudio"""
    
    def test_play_audio_default_params(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.playAudio()
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.PLAY_AUDIO,
                2,  # NodeValues.AUDIO
                1, 49, 49
            ])
    
    def test_play_audio_custom_params(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.playAudio(all=0, folder=52, audio=100)
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.PLAY_AUDIO,
                2,
                0, 52, 100
            ])
    
    def test_play_audio_invalid_folder(self, audio_controller, mock_port_for_audio, capsys):
        audio_controller.playAudio(folder=60)
        
        mock_port_for_audio.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_play_audio_invalid_audio(self, audio_controller, mock_port_for_audio, capsys):
        audio_controller.playAudio(audio=300)
        
        mock_port_for_audio.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_play_audio_boundary_values(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.playAudio(folder=49, audio=49)
            audio_controller.playAudio(folder=57, audio=255)
            
            assert mock_port_for_audio.send_data.call_count == 2


class TestDroidOnOff:
    """Tests para droidOnOf (typo en el nombre)"""
    
    def test_droid_toggle_off_to_on(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.droid_mode = 0
            audio_controller.droidOnOf()
            
            mock_port_for_audio.send_data.assert_called_once()
    
    def test_droid_toggle_on_to_off(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.droid_mode = 1
            audio_controller.droidOnOf()
            
            mock_port_for_audio.send_data.assert_called_once()
    
    def test_droid_exception_handling(self, audio_controller, mock_port_for_audio, capsys):
        mock_port_for_audio.send_data.side_effect = Exception("Port error")
        
        with patch('audio_controller.CommandValues', MagicMock()):
            audio_controller.droidOnOf()
        
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out


class TestEnableAudio:
    """Tests para enableAudio"""
    
    def test_enable_audio_default(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.enableAudio()
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.ENABLE_AUDIO,
                2,
                1, 49, 49
            ])
    
    def test_enable_audio_custom(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.enableAudio(all=0, folder=55, audio=200)
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.ENABLE_AUDIO,
                2,
                0, 55, 200
            ])


class TestDisableAudio:
    """Tests para disableAudio"""
    
    def test_disable_audio_default(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            # Ahora debería funcionar después de corregir el código
            audio_controller.disableAudio()
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.DISABLE_AUDIO,
                2,
                1, 49, 49
            ])


class TestMuteAudio:
    """Tests para muteAudio"""
    
    def test_mute_audio_default(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.muteAudio()
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.MUTE_AUDIO,
                2,
                1, 0
            ])
    
    def test_mute_audio_custom(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.muteAudio(all=0, mute=1)
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.MUTE_AUDIO,
                2,
                0, 1
            ])


class TestIncVolume:
    """Tests para incVolume"""
    
    def test_inc_volume_default(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.incVolume()
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.SET_VOLUME,
                2,
                1, 1
            ])
    
    def test_inc_volume_custom(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.incVolume(all=0)
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.SET_VOLUME,
                2,
                0, 1
            ])


class TestDecVolume:
    """Tests para decVolume"""
    
    def test_dec_volume_default(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.decVolume()  # ← CORREGIDO
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.SET_VOLUME,
                2,
                1, 0
            ])


class TestSetConfiguration:
    """Tests para setConfiguration"""
    
    def test_set_configuration_default(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.setConfiguration()
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.CONFIGURATION,
                2,
                1, 0
            ])
    
    def test_set_configuration_custom(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            audio_controller.setConfiguration(all=0, parameter=5)
            
            mock_port_for_audio.send_data.assert_called_once_with([
                mock_command_values.CONFIGURATION,
                2,
                0, 5
            ])
    
    def test_set_configuration_exception(self, audio_controller, mock_port_for_audio, capsys):
        mock_port_for_audio.send_data.side_effect = Exception("Configuration error")
        
        with patch('audio_controller.CommandValues', MagicMock()):
            audio_controller.setConfiguration()
        
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out


class TestDroidModeToggling:
    """Tests para el toggle del droid mode"""
    
    def test_multiple_toggles(self, audio_controller, mock_port_for_audio, mock_command_values):
        with patch('audio_controller.CommandValues', mock_command_values):
            initial_mode = audio_controller.droid_mode
            
            audio_controller.droidOnOf()
            audio_controller.droidOnOf()
            
            assert mock_port_for_audio.send_data.call_count == 2
