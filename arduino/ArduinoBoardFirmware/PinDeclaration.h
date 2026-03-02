#ifndef PIN_DECLARATION_H
#define PIN_DECLARATION_H

// ---------------------------------------------------------------------------
// LED Pins (adjust to match your wiring)
// ---------------------------------------------------------------------------
const int PIN_LED_1 = 2;
const int PIN_LED_2 = 3;
const int PIN_LED_3 = 4;

// ---------------------------------------------------------------------------
// LCD I2C (typically SDA/SCL are fixed on the board)
// Add LCD I2C address if using LiquidCrystal_I2C
// ---------------------------------------------------------------------------
const int LCD_I2C_ADDRESS = 0x27;
const int LCD_COLS = 16;
const int LCD_ROWS = 2;

// ---------------------------------------------------------------------------
// Buzzer Pin
// ---------------------------------------------------------------------------
const int PIN_BUZZER = 8;

// ---------------------------------------------------------------------------
// Motor Pins (example for a simple DC motor via L298N or similar)
// ---------------------------------------------------------------------------
const int PIN_MOTOR_1_IN1 = 5;
const int PIN_MOTOR_1_IN2 = 6;
const int PIN_MOTOR_1_EN  = 7;

// ---------------------------------------------------------------------------
// Ultrasound Sensor Pins (HC-SR04)
// ---------------------------------------------------------------------------
const int PIN_ULTRASOUND_TRIG = 9;
const int PIN_ULTRASOUND_ECHO = 10;

#endif // PIN_DECLARATION_H
