import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
from pathlib import Path

# Añadir el directorio core al path
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

@pytest.fixture
def mock_command_values():
    """Mock de CommandValues"""
    class MockCommandValues:
        # Servo commands
        MOVE_SERVO_SLOW = 1
        MOVE_SERVO_FAST = 2
        SET_SERVO_INIT_POS = 3
        MOVE_SERVO_TO_INIT_POS = 4
        SET_SERVO_SECUENCE = 5
        PLAY_SERVO_SECUENCE = 6
        STOP_SERVO_SECUENCE = 7
        SCAPE_SERVO_SECUENCE = 8
        SET_PROGRAM = 9
        
        # Audio commands
        PLAY_AUDIO = 10
        DROID = 11
        ENABLE_AUDIO = 12
        DISABLE_AUDIO = 13
        MUTE_AUDIO = 14
        SET_VOLUME = 15
        CONFIGURATION = 16
        
        # Teece commands
        SET_TEECE_COLOR = 17
        SET_TEECE_TEXT = 18
    
    return MockCommandValues

@pytest.fixture
def mock_node_values():
    """Mock de NodeValues"""
    class MockNodeValues:
        SERVO = 1
        AUDIO = 2
        TEECE_COLOR = 3
        TEECE_COMMAND_TEXT = 4
    
    return MockNodeValues
