#ifndef HARDWARE_DECLARATION_H
#define HARDWARE_DECLARATION_H

#define MAX_LED_OBSERVERS 2
#define MAX_LCD_OBSERVERS 0
#define MAX_BUZZER_OBSERVERS 0
#define MAX_MOTOR_OBSERVERS 4
#define MAX_ULTRASOUND_OBSERVERS 2
#define MAX_EYES_OBSERVERS 2

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
const int PIN_MOTOR_1_EN = 7;

// ---------------------------------------------------------------------------
// Ultrasound Sensor Pins (HC-SR04)
// ---------------------------------------------------------------------------
#define ULTRADOUNS_1_ID "US_1"
#define ULTRADOUNS_1_ECHO_PIN 2
#define ULTRADOUNS_1_TRIG_PIN 3
const int PIN_ULTRASOUND_TRIG = 9;
const int PIN_ULTRASOUND_ECHO = 10;

// ── Eyes (GC9A01 × 2, SPI hardware) ─────────────────────────────────────
// Arduino Mega 2560: SCK=52, MOSI=51 (hardware SPI, no declarar aquí)
#define PIN_EYES_CS_LEFT 10
#define PIN_EYES_CS_RIGHT 9
#define PIN_EYES_DC 8
#define PIN_EYES_RST 7

#endif // PIN_DECLARATION_H
