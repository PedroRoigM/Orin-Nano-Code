import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Crear mocks antes de importar
sys.modules['commandValues'] = MagicMock()
sys.modules['nodeValues'] = MagicMock()
sys.modules['port'] = MagicMock()

# Configurar NodeValues mock
sys.modules['nodeValues'].NodeValues = MagicMock()
sys.modules['nodeValues'].NodeValues.TEECE_COLOR = 3
sys.modules['nodeValues'].NodeValues.TEECE_COMMAND_TEXT = 4

from teece_controller import TeeceController, DisplayValues, ProgramMode


@pytest.fixture
def mock_port_for_teece():
    """Mock del Port para teece controller"""
    with patch('teece_controller.Port') as mock:
        port_instance = MagicMock()
        mock.return_value = port_instance
        yield port_instance


@pytest.fixture
def teece_controller(mock_port_for_teece):
    """Instancia de TeeceController con Port mockeado"""
    return TeeceController()


class TestDisplayValues:
    """Tests para DisplayValues enum"""
    
    def test_all_teeces_value(self):
        assert DisplayValues.ALL_TEECES == 1
    
    def test_top_fld_value(self):
        assert DisplayValues.TOP_FLD == 2
    
    def test_bottom_fld_value(self):
        assert DisplayValues.BOTTOM_FLD == 3
    
    def test_rear_fld_value(self):
        assert DisplayValues.REAR_FLD == 4
    
    def test_front_psi_value(self):
        assert DisplayValues.FRONT_PSI == 5
    
    def test_rear_psi_value(self):
        assert DisplayValues.REAR_PSI == 6
    
    def test_magic_lights_value(self):
        assert DisplayValues.MAGIC_LIGHTS == 7


class TestProgramMode:
    """Tests para ProgramMode enum"""
    
    def test_off_value(self):
        assert ProgramMode.OFF == 49
    
    def test_random_value(self):
        assert ProgramMode.RANDOM == 50
    
    def test_alarm_value(self):
        assert ProgramMode.ALARM == 51
    
    def test_error_value(self):
        assert ProgramMode.ERROR == 52
    
    def test_leia_value(self):
        assert ProgramMode.LEIA == 53
    
    def test_starwars_value(self):
        assert ProgramMode.STARWARS == 54
    
    def test_imperial_value(self):
        assert ProgramMode.IMPERIAL == 55
    
    def test_barcode_value(self):
        assert ProgramMode.BARCODE == 56


class TestTeeceControllerInit:
    """Tests para inicialización"""
    
    def test_init_default_port(self, mock_port_for_teece):
        controller = TeeceController()
        assert controller.port is not None
    
    def test_init_custom_port(self):
        with patch('teece_controller.Port') as mock:
            controller = TeeceController('/dev/ttyUSB0')
            mock.assert_called_once_with('/dev/ttyUSB0')


class TestTeeceValidation:
    """Tests para métodos de validación"""
    
    def test_is_color_valid_in_range(self, teece_controller):
        # No debería lanzar excepción
        teece_controller._isColorValid(0)
        teece_controller._isColorValid(128)
        teece_controller._isColorValid(255)
    
    def test_is_color_valid_below_range(self, teece_controller):
        with pytest.raises(ValueError, match="Color value not in valid range"):
            teece_controller._isColorValid(-1)
    
    def test_is_color_valid_above_range(self, teece_controller):
        with pytest.raises(ValueError, match="Color value not in valid range"):
            teece_controller._isColorValid(256)
    
    def test_is_program_valid_in_range(self, teece_controller):
        teece_controller._isProgramValid(49)
        teece_controller._isProgramValid(52)
        teece_controller._isProgramValid(56)
    
    def test_is_program_valid_below_range(self, teece_controller):
        with pytest.raises(ValueError, match="Program not valid"):
            teece_controller._isProgramValid(48)
    
    def test_is_program_valid_above_range(self, teece_controller):
        with pytest.raises(ValueError, match="Program not valid"):
            teece_controller._isProgramValid(57)
    
    def test_is_text_valid_min_length(self, teece_controller):
        teece_controller._isTextValid(['a'])
    
    def test_is_text_valid_max_length(self, teece_controller):
        teece_controller._isTextValid(['a'] * 30)
    
    def test_is_text_valid_empty_list(self, teece_controller):
        with pytest.raises(ValueError, match="Text len is not valid"):
            teece_controller._isTextValid([])
    
    def test_is_text_valid_too_long(self, teece_controller):
        with pytest.raises(ValueError, match="Text len is not valid"):
            teece_controller._isTextValid(['a'] * 31)


class TestSetColor:
    """Tests para setColor"""
    
    def test_set_color_valid(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            colors = [255, 128, 64, 32]  # red, green, blue, white
            teece_controller.setColor(DisplayValues.ALL_TEECES, colors)
            
            mock_port_for_teece.send_data.assert_called_once_with([
                mock_command_values.SET_TEECE_COLOR,
                3,  # NodeValues.TEECE_COLOR
                DisplayValues.ALL_TEECES,
                255, 128, 64, 32
            ])
    
    def test_set_color_all_zeros(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            colors = [0, 0, 0, 0]
            teece_controller.setColor(DisplayValues.TOP_FLD, colors)
            
            mock_port_for_teece.send_data.assert_called_once_with([
                mock_command_values.SET_TEECE_COLOR,
                3,
                DisplayValues.TOP_FLD,
                0, 0, 0, 0
            ])
    
    def test_set_color_all_max(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            colors = [255, 255, 255, 255]
            teece_controller.setColor(DisplayValues.MAGIC_LIGHTS, colors)
            
            mock_port_for_teece.send_data.assert_called_once_with([
                mock_command_values.SET_TEECE_COLOR,
                3,
                DisplayValues.MAGIC_LIGHTS,
                255, 255, 255, 255
            ])
    
    def test_set_color_invalid_color_value(self, teece_controller, mock_port_for_teece, capsys):
        colors = [255, 300, 64, 32]  # 300 is invalid
        teece_controller.setColor(DisplayValues.ALL_TEECES, colors)
        
        mock_port_for_teece.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_set_color_negative_value(self, teece_controller, mock_port_for_teece, capsys):
        colors = [255, -10, 64, 32]  # -10 is invalid
        teece_controller.setColor(DisplayValues.ALL_TEECES, colors)
        
        mock_port_for_teece.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_set_color_insufficient_colors(self, teece_controller, mock_port_for_teece, capsys):
        colors = [255, 128, 64]  # Solo 3 colores, faltan 4
        teece_controller.setColor(DisplayValues.ALL_TEECES, colors)
        
        mock_port_for_teece.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_set_color_port_exception(self, teece_controller, mock_port_for_teece, capsys):
        mock_port_for_teece.send_data.side_effect = Exception("Port error")
        
        with patch('teece_controller.CommandValues', MagicMock()):
            colors = [255, 128, 64, 32]
            teece_controller.setColor(DisplayValues.ALL_TEECES, colors)
        
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out


class TestSetProgram:
    """Tests para setProgram"""
    
    def test_set_program_off(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            teece_controller.setProgram(DisplayValues.ALL_TEECES, ProgramMode.OFF)
            
            mock_port_for_teece.send_data.assert_called_once_with([
                mock_command_values.SET_PROGRAM,
                4,  # NodeValues.TEECE_COMMAND_TEXT
                DisplayValues.ALL_TEECES,
                ProgramMode.OFF
            ])
    
    def test_set_program_random(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            teece_controller.setProgram(DisplayValues.TOP_FLD, ProgramMode.RANDOM)
            
            mock_port_for_teece.send_data.assert_called_once_with([
                mock_command_values.SET_PROGRAM,
                4,
                DisplayValues.TOP_FLD,
                ProgramMode.RANDOM
            ])
    
    def test_set_program_starwars(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            teece_controller.setProgram(DisplayValues.MAGIC_LIGHTS, ProgramMode.STARWARS)
            
            mock_port_for_teece.send_data.assert_called_once_with([
                mock_command_values.SET_PROGRAM,
                4,
                DisplayValues.MAGIC_LIGHTS,
                ProgramMode.STARWARS
            ])
    
    def test_set_program_invalid_below(self, teece_controller, mock_port_for_teece, capsys):
        teece_controller.setProgram(DisplayValues.ALL_TEECES, 48)
        
        mock_port_for_teece.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_set_program_invalid_above(self, teece_controller, mock_port_for_teece, capsys):
        teece_controller.setProgram(DisplayValues.ALL_TEECES, 57)
        
        mock_port_for_teece.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_set_program_boundary_values(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            teece_controller.setProgram(DisplayValues.ALL_TEECES, 49)
            teece_controller.setProgram(DisplayValues.ALL_TEECES, 56)
            
            assert mock_port_for_teece.send_data.call_count == 2
    
    def test_set_program_exception_handling(self, teece_controller, mock_port_for_teece, capsys):
        mock_port_for_teece.send_data.side_effect = Exception("Port error")
        
        with patch('teece_controller.CommandValues', MagicMock()):
            teece_controller.setProgram(DisplayValues.ALL_TEECES, ProgramMode.OFF)
        
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out


class TestTransformTextToASCII:
    """Tests para _transformTextToASCII"""
    
    def test_transform_single_char(self, teece_controller):
        text = ['A']
        result = teece_controller._transformTextToASCII(text)
        assert result == [65]
    
    def test_transform_multiple_chars(self, teece_controller):
        text = ['H', 'e', 'l', 'l', 'o']
        result = teece_controller._transformTextToASCII(text)
        assert result == [72, 101, 108, 108, 111]
    
    def test_transform_numbers(self, teece_controller):
        text = ['1', '2', '3']
        result = teece_controller._transformTextToASCII(text)
        assert result == [49, 50, 51]
    
    def test_transform_special_chars(self, teece_controller):
        text = ['!', '@', '#']
        result = teece_controller._transformTextToASCII(text)
        assert result == [33, 64, 35]
    
    def test_transform_empty_list(self, teece_controller):
        text = []
        result = teece_controller._transformTextToASCII(text)
        assert result == []
    
    def test_transform_spaces(self, teece_controller):
        text = ['A', ' ', 'B']
        result = teece_controller._transformTextToASCII(text)
        assert result == [65, 32, 66]


class TestSetText:
    """Tests para setText"""
    
    def test_set_text_single_char(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            text = ['A']
            teece_controller.setText(DisplayValues.ALL_TEECES, text)
            
            expected_command = [
                mock_command_values.SET_TEECE_TEXT,
                4,  # NodeValues.TEECE_COMMAND_TEXT
                DisplayValues.ALL_TEECES,
                65  # ASCII for 'A'
            ]
            mock_port_for_teece.send_data.assert_called_once_with(expected_command)
    
    def test_set_text_word(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            text = ['H', 'i']
            teece_controller.setText(DisplayValues.TOP_FLD, text)
            
            expected_command = [
                mock_command_values.SET_TEECE_TEXT,
                4,
                DisplayValues.TOP_FLD,
                72, 105  # ASCII for 'H', 'i'
            ]
            mock_port_for_teece.send_data.assert_called_once_with(expected_command)
    
    def test_set_text_sentence(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            text = ['R', '2', '-', 'D', '2']
            teece_controller.setText(DisplayValues.FRONT_PSI, text)
            
            expected_command = [
                mock_command_values.SET_TEECE_TEXT,
                4,
                DisplayValues.FRONT_PSI,
                82, 50, 45, 68, 50  # ASCII values
            ]
            mock_port_for_teece.send_data.assert_called_once_with(expected_command)
    
    def test_set_text_max_length(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            text = ['A'] * 30  # Maximum length
            teece_controller.setText(DisplayValues.ALL_TEECES, text)
            
            expected_command = [
                mock_command_values.SET_TEECE_TEXT,
                4,
                DisplayValues.ALL_TEECES
            ] + [65] * 30
            mock_port_for_teece.send_data.assert_called_once_with(expected_command)
    
    def test_set_text_empty_list(self, teece_controller, mock_port_for_teece, capsys):
        text = []
        teece_controller.setText(DisplayValues.ALL_TEECES, text)
        
        mock_port_for_teece.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_set_text_too_long(self, teece_controller, mock_port_for_teece, capsys):
        text = ['A'] * 31  # Over maximum
        teece_controller.setText(DisplayValues.ALL_TEECES, text)
        
        mock_port_for_teece.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_set_text_with_numbers(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            text = ['1', '2', '3', '4', '5']
            teece_controller.setText(DisplayValues.REAR_PSI, text)
            
            expected_command = [
                mock_command_values.SET_TEECE_TEXT,
                4,
                DisplayValues.REAR_PSI,
                49, 50, 51, 52, 53  # ASCII for '1', '2', '3', '4', '5'
            ]
            mock_port_for_teece.send_data.assert_called_once_with(expected_command)
    
    def test_set_text_exception_handling(self, teece_controller, mock_port_for_teece, capsys):
        mock_port_for_teece.send_data.side_effect = Exception("Port error")
        
        with patch('teece_controller.CommandValues', MagicMock()):
            text = ['T', 'e', 's', 't']
            teece_controller.setText(DisplayValues.ALL_TEECES, text)
        
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out


class TestIntegrationScenarios:
    """Tests de integración para escenarios completos"""
    
    def test_set_color_and_program(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            # Set color first
            colors = [255, 0, 0, 0]  # Red
            teece_controller.setColor(DisplayValues.ALL_TEECES, colors)
            
            # Then set program
            teece_controller.setProgram(DisplayValues.ALL_TEECES, ProgramMode.STARWARS)
            
            assert mock_port_for_teece.send_data.call_count == 2
    
    def test_set_text_on_multiple_displays(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            teece_controller.setText(DisplayValues.TOP_FLD, ['T', 'O', 'P'])
            teece_controller.setText(DisplayValues.BOTTOM_FLD, ['B', 'O', 'T'])
            teece_controller.setText(DisplayValues.REAR_FLD, ['R', 'E', 'A', 'R'])
            
            assert mock_port_for_teece.send_data.call_count == 3
    
    def test_all_display_values(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            displays = [
                DisplayValues.ALL_TEECES,
                DisplayValues.TOP_FLD,
                DisplayValues.BOTTOM_FLD,
                DisplayValues.REAR_FLD,
                DisplayValues.FRONT_PSI,
                DisplayValues.REAR_PSI,
                DisplayValues.MAGIC_LIGHTS
            ]
            
            for display in displays:
                teece_controller.setProgram(display, ProgramMode.OFF)
            
            assert mock_port_for_teece.send_data.call_count == len(displays)
    
    def test_all_program_modes(self, teece_controller, mock_port_for_teece, mock_command_values):
        with patch('teece_controller.CommandValues', mock_command_values):
            programs = [
                ProgramMode.OFF,
                ProgramMode.RANDOM,
                ProgramMode.ALARM,
                ProgramMode.ERROR,
                ProgramMode.LEIA,
                ProgramMode.STARWARS,
                ProgramMode.IMPERIAL,
                ProgramMode.BARCODE
            ]
            
            for program in programs:
                teece_controller.setProgram(DisplayValues.ALL_TEECES, program)
            
            assert mock_port_for_teece.send_data.call_count == len(programs)
