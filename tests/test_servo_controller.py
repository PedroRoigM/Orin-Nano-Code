import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Crear mocks antes de importar
sys.modules['commandValues'] = MagicMock()

from servo_controller import ServoController, NodeValues


@pytest.fixture
def mock_port_for_servo():
    """Mock del Port para servo controller"""
    with patch('servo_controller.Port') as mock:
        port_instance = MagicMock()
        mock.return_value = port_instance
        yield port_instance


@pytest.fixture
def servo_controller(mock_port_for_servo):
    """Instancia de ServoController con Port mockeado"""
    return ServoController()


class TestNodeValues:
    """Tests para NodeValues enum"""
    
    def test_servo_value(self):
        assert NodeValues.SERVO == 1


class TestServoControllerInit:
    """Tests para inicialización"""
    
    def test_init_default_port(self, mock_port_for_servo):
        controller = ServoController()
        assert controller.port is not None
    
    def test_init_custom_port(self):
        with patch('servo_controller.Port') as mock:
            controller = ServoController('/dev/ttyUSB0')
            mock.assert_called_once_with('/dev/ttyUSB0')


class TestServoValidation:
    """Tests para métodos de validación"""
    
    def test_is_position_valid_in_range(self, servo_controller):
        # No debería lanzar excepción
        servo_controller._isPositionValid(0)
        servo_controller._isPositionValid(128)
        servo_controller._isPositionValid(255)
    
    def test_is_position_valid_below_range(self, servo_controller):
        with pytest.raises(ValueError, match="Servo position not in range"):
            servo_controller._isPositionValid(-1)
    
    def test_is_position_valid_above_range(self, servo_controller):
        with pytest.raises(ValueError, match="Servo position not in range"):
            servo_controller._isPositionValid(256)
    
    def test_is_servo_number_valid_in_range(self, servo_controller):
        servo_controller._isServoNumberValid(0)
        servo_controller._isServoNumberValid(24)
        servo_controller._isServoNumberValid(47)
    
    def test_is_servo_number_valid_below_range(self, servo_controller):
        with pytest.raises(ValueError, match="Servo number not in range"):
            servo_controller._isServoNumberValid(-1)
    
    def test_is_servo_number_valid_above_range(self, servo_controller):
        with pytest.raises(ValueError, match="Servo number not in range"):
            servo_controller._isServoNumberValid(48)


class TestMoveServoSlow:
    """Tests para moveServoSlow"""
    
    def test_move_servo_slow_valid(self, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.moveServoSlow(1, 10, 128)
            
            mock_port_for_servo.send_data.assert_called_once_with([
                mock_command_values.MOVE_SERVO_SLOW,
                NodeValues.SERVO,
                1, 10, 128
            ])
    
    def test_move_servo_slow_invalid_position(self, servo_controller, mock_port_for_servo, capsys):
        servo_controller.moveServoSlow(1, 10, 300)
        
        mock_port_for_servo.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_move_servo_slow_invalid_servo_number(self, servo_controller, mock_port_for_servo, capsys):
        servo_controller.moveServoSlow(1, 50, 128)
        
        mock_port_for_servo.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_move_servo_slow_boundary_values(self, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.moveServoSlow(0, 0, 0)
            servo_controller.moveServoSlow(1, 47, 255)
            
            assert mock_port_for_servo.send_data.call_count == 2


class TestMoveServoFast:
    """Tests para moveServoFast"""
    
    def test_move_servo_fast_valid(self, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.moveServoFast(1, 5, 200)
            
            mock_port_for_servo.send_data.assert_called_once_with([
                mock_command_values.MOVE_SERVO_FAST,
                NodeValues.SERVO,
                1, 5, 200
            ])
    
    def test_move_servo_fast_exception_handling(self, servo_controller, mock_port_for_servo, capsys):
        mock_port_for_servo.send_data.side_effect = Exception("Port error")
        
        with patch('servo_controller.CommandValues', MagicMock()):
            servo_controller.moveServoFast(1, 10, 128)
        
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out


class TestSetServoInitialPosition:
    """Tests para setServoInitialPosition"""
    
    def test_set_servo_initial_position_valid(self, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.setServoInitialPosition(1, 15, 90)
            
            mock_port_for_servo.send_data.assert_called_once_with([
                mock_command_values.SET_SERVO_INIT_POS,
                NodeValues.SERVO,
                1, 15, 90
            ])


class TestMoveServoToInitialPosition:
    """Tests para moveServoToInitialPosition"""
    
    def test_move_to_initial_position_valid(self, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.moveServoToInitialPosition(1, 20, 100)
            
            mock_port_for_servo.send_data.assert_called_once_with([
                mock_command_values.MOVE_SERVO_TO_INIT_POS,
                NodeValues.SERVO,
                1, 20, 100
            ])


class TestSetServoSecuence:
    """Tests para setServoSecuence"""
    
    def test_set_servo_sequence_valid(self, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.setServoSecuence(1, 200, 50)
            
            mock_port_for_servo.send_data.assert_called_once_with([
                mock_command_values.SET_SERVO_SECUENCE,
                NodeValues.SERVO,
                1, 200, 50
            ])
    
    def test_set_servo_sequence_invalid_high(self, servo_controller, mock_port_for_servo, capsys):
        servo_controller.setServoSecuence(1, 300, 50)
        
        mock_port_for_servo.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    def test_set_servo_sequence_invalid_low(self, servo_controller, mock_port_for_servo, capsys):
        servo_controller.setServoSecuence(1, 200, -10)
        
        mock_port_for_servo.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out


class TestPlayServoSecuence:
    """Tests para playServoSecuence"""
    
    def test_play_servo_sequence(self, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.playServoSecuence(1)
            
            mock_port_for_servo.send_data.assert_called_once_with([
                mock_command_values.PLAY_SERVO_SECUENCE,
                NodeValues.SERVO,
                1
            ])


class TestStopServoSecuence:
    """Tests para stopServoSecuence"""
    
    def test_stop_servo_sequence(self, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.stopServoSecuence(1)
            
            mock_port_for_servo.send_data.assert_called_once_with([
                mock_command_values.STOP_SERVO_SECUENCE,
                NodeValues.SERVO,
                1
            ])


class TestScapeServoSecuence:
    """Tests para scapeServoSecuecne (typo en el nombre)"""
    
    def test_scape_servo_sequence(self, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.scapeServoSecuecne(1)
            
            mock_port_for_servo.send_data.assert_called_once_with([
                mock_command_values.SCAPE_SERVO_SECUENCE,
                NodeValues.SERVO,
                1
            ])


class TestSetAllServosPosition:
    """Tests para setAllServosPosition"""
    
    @patch('servo_controller.ServoController._isPositionValid')
    def test_set_all_servos_position_valid(self, mock_validate, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            positions = [100, 150, 200, 50, 75]
            servo_controller.setAllServosPosition(1, positions)
            
            # Verificar que se validaron todas las posiciones
            assert mock_validate.call_count == len(positions)
            
            # Verificar el comando enviado
            expected_command = [mock_command_values.SET_PROGRAM, NodeValues.SERVO, 1] + positions
            mock_port_for_servo.send_data.assert_called_once_with(expected_command)
    
    @patch('servo_controller.ServoController._isPositionValid')
    def test_set_all_servos_position_invalid(self, mock_validate, servo_controller, mock_port_for_servo, capsys):
        mock_validate.side_effect = ValueError("Invalid position")
        
        with patch('servo_controller.CommandValues', MagicMock()):
            servo_controller.setAllServosPosition(1, [100, 300, 200])
        
        mock_port_for_servo.send_data.assert_not_called()
        captured = capsys.readouterr()
        assert "ERROR:" in captured.out
    
    @patch('servo_controller.ServoController._isPositionValid')
    def test_set_all_servos_empty_list(self, mock_validate, servo_controller, mock_port_for_servo, mock_command_values):
        with patch('servo_controller.CommandValues', mock_command_values):
            servo_controller.setAllServosPosition(1, [])
            
            mock_validate.assert_not_called()
            expected_command = [mock_command_values.SET_PROGRAM, NodeValues.SERVO, 1]
            mock_port_for_servo.send_data.assert_called_once_with(expected_command)
