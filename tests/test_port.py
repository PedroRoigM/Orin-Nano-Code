import pytest
from unittest.mock import Mock, patch, MagicMock
import serial
from port import Port, BufferValues


class TestBufferValues:
    """Tests para los valores del buffer"""
    
    def test_buffer_start_value(self):
        assert BufferValues.BUFFER_START == 64
    
    def test_buffer_end_value(self):
        assert BufferValues.BUFFER_END == 13


class TestPortInit:
    """Tests para la inicialización del Port"""
    
    @patch('serial.Serial')
    def test_init_default_port(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        
        assert port.port_name == '/dev/ttyACM0'
        assert port.connection == mock_serial_instance
    
    @patch('serial.Serial')
    def test_init_custom_port(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port('/dev/ttyUSB0')
        
        assert port.port_name == '/dev/ttyUSB0'
        assert mock_serial_instance.port == '/dev/ttyUSB0'
    
    @patch('serial.Serial')
    def test_init_port_with_whitespace(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port('  /dev/ttyACM1  ')
        
        assert port.port_name == '/dev/ttyACM1'
        assert mock_serial_instance.port == '/dev/ttyACM1'
    
    @patch('serial.Serial')
    def test_init_serial_configuration(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        
        assert mock_serial_instance.baudrate == 9600
        assert mock_serial_instance.bytesize == serial.EIGHTBITS
        assert mock_serial_instance.stopbits == serial.STOPBITS_ONE
        assert mock_serial_instance.parity == serial.PARITY_NONE
        assert mock_serial_instance.timeout == 1


class TestPortSendData:
    """Tests para el envío de datos"""
    
    @patch('serial.Serial')
    def test_send_data_basic(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False
        
        # Simular que cuando se abre, is_open cambia a True
        def mock_open():
            mock_serial_instance.is_open = True
        
        def mock_close():
            mock_serial_instance.is_open = False
        
        mock_serial_instance.open.side_effect = mock_open
        mock_serial_instance.close.side_effect = mock_close
        
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        data = [1, 2, 3, 4, 5]
        
        result = port.send_data(data)
        
        # Verificar que se abrió el puerto
        mock_serial_instance.open.assert_called_once()
        
        # Verificar el buffer enviado
        expected_buffer = bytes([BufferValues.BUFFER_START] + data + [BufferValues.BUFFER_END])
        mock_serial_instance.write.assert_called_once_with(expected_buffer)
        
        # Verificar flush y close
        mock_serial_instance.flush.assert_called_once()
        mock_serial_instance.close.assert_called_once()
        
        # Verificar el resultado
        assert result == list(expected_buffer)
    
    @patch('serial.Serial')
    def test_send_data_empty_list(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False
        
        def mock_open():
            mock_serial_instance.is_open = True
        
        def mock_close():
            mock_serial_instance.is_open = False
        
        mock_serial_instance.open.side_effect = mock_open
        mock_serial_instance.close.side_effect = mock_close
        
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        data = []
        
        result = port.send_data(data)
        
        expected_buffer = bytes([BufferValues.BUFFER_START, BufferValues.BUFFER_END])
        mock_serial_instance.write.assert_called_once_with(expected_buffer)
        assert result == list(expected_buffer)
    
    @patch('serial.Serial')
    def test_send_data_single_value(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False
        
        def mock_open():
            mock_serial_instance.is_open = True
        
        def mock_close():
            mock_serial_instance.is_open = False
        
        mock_serial_instance.open.side_effect = mock_open
        mock_serial_instance.close.side_effect = mock_close
        
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        data = [100]
        
        result = port.send_data(data)
        
        expected_buffer = bytes([BufferValues.BUFFER_START, 100, BufferValues.BUFFER_END])
        assert result == list(expected_buffer)
    
    @patch('serial.Serial')
    def test_send_data_port_already_open(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = True
        
        def mock_close():
            mock_serial_instance.is_open = False
        
        mock_serial_instance.close.side_effect = mock_close
        
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        port.send_data([1, 2, 3])
        
        # No debería llamar a open() si ya está abierto
        mock_serial_instance.open.assert_not_called()
        # Pero sí debe cerrar
        mock_serial_instance.close.assert_called_once()
    
    @patch('serial.Serial')
    def test_send_data_closes_port_on_error(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False
        
        # Simular que cuando se abre, is_open cambia a True
        def mock_open():
            mock_serial_instance.is_open = True
        
        def mock_close():
            mock_serial_instance.is_open = False
        
        mock_serial_instance.open.side_effect = mock_open
        mock_serial_instance.close.side_effect = mock_close
        
        # El error ocurre en write
        mock_serial_instance.write.side_effect = serial.SerialException("Error de escritura")
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        
        with pytest.raises(serial.SerialException):
            port.send_data([1, 2, 3])
        
        # Verificar que se cerró el puerto incluso con error
        mock_serial_instance.close.assert_called_once()
    
    @patch('serial.Serial')
    def test_send_data_handles_write_exception(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False
        
        def mock_open():
            mock_serial_instance.is_open = True
        
        def mock_close():
            mock_serial_instance.is_open = False
        
        mock_serial_instance.open.side_effect = mock_open
        mock_serial_instance.close.side_effect = mock_close
        
        mock_serial_instance.write.side_effect = Exception("Hardware error")
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        
        with pytest.raises(Exception, match="Hardware error"):
            port.send_data([1, 2, 3])
    
    @patch('serial.Serial')
    def test_send_data_with_max_values(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False
        
        def mock_open():
            mock_serial_instance.is_open = True
        
        def mock_close():
            mock_serial_instance.is_open = False
        
        mock_serial_instance.open.side_effect = mock_open
        mock_serial_instance.close.side_effect = mock_close
        
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        data = [255] * 10
        
        result = port.send_data(data)
        
        expected_buffer = bytes([BufferValues.BUFFER_START] + data + [BufferValues.BUFFER_END])
        assert result == list(expected_buffer)


class TestPortListSerialPorts:
    """Tests para listar puertos seriales"""
    
    @patch('serial.tools.list_ports.comports')
    def test_list_serial_ports(self, mock_comports):
        mock_comports.return_value = [
            Mock(device='/dev/ttyACM0', description='Arduino'),
            Mock(device='/dev/ttyACM1', description='Arduino'),
        ]
        
        ports = Port.list_serial_ports()
        
        assert len(ports) == 2
        assert ports[0].device == '/dev/ttyACM0'
        assert ports[1].device == '/dev/ttyACM1'
    
    @patch('serial.tools.list_ports.comports')
    def test_list_serial_ports_empty(self, mock_comports):
        mock_comports.return_value = []
        
        ports = Port.list_serial_ports()
        
        assert len(ports) == 0
    
    @patch('serial.tools.list_ports.comports')
    def test_list_serial_ports_returns_comports(self, mock_comports):
        mock_comports.return_value = [Mock(device='/dev/ttyACM0')]
        
        result = Port.list_serial_ports()
        
        mock_comports.assert_called_once()
        assert result is not None


class TestPortIntegration:
    """Tests de integración"""
    
    @patch('serial.Serial')
    def test_multiple_send_operations(self, mock_serial_class):
        mock_serial_instance = MagicMock()
        mock_serial_instance.is_open = False
        
        # Simular open/close correctamente
        def mock_open():
            mock_serial_instance.is_open = True
        
        def mock_close():
            mock_serial_instance.is_open = False
        
        mock_serial_instance.open.side_effect = mock_open
        mock_serial_instance.close.side_effect = mock_close
        
        mock_serial_class.return_value = mock_serial_instance
        
        port = Port()
        
        port.send_data([1, 2, 3])
        port.send_data([4, 5, 6])
        port.send_data([7, 8, 9])
        
        # Verificar que se llamó 3 veces a cada operación
        assert mock_serial_instance.open.call_count == 3
        assert mock_serial_instance.write.call_count == 3
        assert mock_serial_instance.flush.call_count == 3
        assert mock_serial_instance.close.call_count == 3
    
    @patch('serial.Serial')
    def test_send_data_different_port_names(self, mock_serial_class):
        mock_serial_instance1 = MagicMock()
        mock_serial_instance1.is_open = False
        
        def mock_open1():
            mock_serial_instance1.is_open = True
        
        def mock_close1():
            mock_serial_instance1.is_open = False
        
        mock_serial_instance1.open.side_effect = mock_open1
        mock_serial_instance1.close.side_effect = mock_close1
        
        mock_serial_instance2 = MagicMock()
        mock_serial_instance2.is_open = False
        
        def mock_open2():
            mock_serial_instance2.is_open = True
        
        def mock_close2():
            mock_serial_instance2.is_open = False
        
        mock_serial_instance2.open.side_effect = mock_open2
        mock_serial_instance2.close.side_effect = mock_close2
        
        mock_serial_class.side_effect = [mock_serial_instance1, mock_serial_instance2]
        
        port1 = Port('/dev/ttyACM0')
        port2 = Port('/dev/ttyACM1')
        
        assert port1.port_name != port2.port_name
        assert port1.port_name == '/dev/ttyACM0'
        assert port2.port_name == '/dev/ttyACM1'
        
        port1.send_data([1])
        port2.send_data([2])
