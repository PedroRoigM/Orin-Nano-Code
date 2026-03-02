from enum import IntEnum

class CommandValues(IntEnum):
	ENABLE_AUDIO = 66
	DISABLE_AUDIO = 67
	TANK_DRIVE = 68          # 'D' — left/right wheel speed
	DROID = 69
	SCAPE_SERVO_SECUENCE = 69
	LED_COLOR = 72           # 'H' — set LED RGB color
	SET_SERVO_INIT_POS = 73
	MOVE_SERVO_TO_INIT_POS = 74
	MOVE_SERVO_SLOW = 75
	SET_TEECE_COLOR = 76
	SET_HOLO_COLOR = 76
	MUTE_AUDIO = 77
	SET_TEECE_TEXT = 77
	PLAY_SERVO_SECUENCE = 77
	CHANGE_HOLO_PROGRAM = 77
	STOP_SERVO_SECUENCE = 78
	SET_SERVO_SECUENCE = 79
	LED_BRIGHTNESS = 80      # 'P' — set LED brightness
	LED_PATTERN = 81         # 'Q' — set LED animation pattern
	LCD_TEXT = 82            # 'R' — write text to LCD
	MOVE_SERVO_FAST = 83
	SET_PROGRAM = 84
	LCD_CLEAR = 85           # 'U' — clear LCD display
	SET_VOLUMEN = 86
	MOVE_HOLO_SERVO = 87
	PLAY_AUDIO = 87
	CONFIGURATION = 90
