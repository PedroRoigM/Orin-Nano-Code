#ifndef HARDWARE_DECLARATION_H
#define HARDWARE_DECLARATION_H

// ---------------------------------------------------------------------------
// Observer counts — determines array sizes in Coordinator
// ---------------------------------------------------------------------------
#define MAX_LED_OBSERVERS        2
#define MAX_LCD_OBSERVERS        0
#define MAX_BUZZER_OBSERVERS     0
#define MAX_MOTOR_OBSERVERS      4
#define MAX_ULTRASOUND_OBSERVERS 2
#define MAX_EYES_OBSERVERS       2

// ---------------------------------------------------------------------------
// LED Pins  (Arduino Mega digital pins 22-23)
// ---------------------------------------------------------------------------
#define PIN_LED_1   22
#define PIN_LED_2   23

// ---------------------------------------------------------------------------
// LCD I2C
// SDA = pin 20 (Mega), SCL = pin 21 (Mega)  — fixed by hardware, declared here for reference
// ---------------------------------------------------------------------------
#define LCD_I2C_ADDRESS  0x27
#define LCD_COLS         16
#define LCD_ROWS         2

// ---------------------------------------------------------------------------
// Buzzer Pin  (Mega pin 24)
// ---------------------------------------------------------------------------
// #define PIN_BUZZER  24

// ---------------------------------------------------------------------------
// Motor Pins  (L298N or similar, 4 motors × 3 pins = 12 pins, Mega 25-36)
// ---------------------------------------------------------------------------
#define PIN_MOTOR_1_IN1  25
#define PIN_MOTOR_1_IN2  26
#define PIN_MOTOR_1_EN   27

#define PIN_MOTOR_2_IN1  28
#define PIN_MOTOR_2_IN2  29
#define PIN_MOTOR_2_EN   30

#define PIN_MOTOR_3_IN1  31
#define PIN_MOTOR_3_IN2  32
#define PIN_MOTOR_3_EN   33

#define PIN_MOTOR_4_IN1  34
#define PIN_MOTOR_4_IN2  35
#define PIN_MOTOR_4_EN   36

// ---------------------------------------------------------------------------
// Ultrasound Sensor Pins  (HC-SR04 × 2, Mega pins 37-40)
// ---------------------------------------------------------------------------
#define ULTRASOUND_1_ECHO_PIN  37
#define ULTRASOUND_1_TRIG_PIN  38
#define ULTRASOUND_2_ECHO_PIN  39
#define ULTRASOUND_2_TRIG_PIN  40

// ---------------------------------------------------------------------------
// Eyes  (GC9A01 × 2, hardware SPI on Mega: SCK=52, MOSI=51 — declared here for reference)
// ---------------------------------------------------------------------------
#define PIN_EYES_CS_LEFT   53
#define PIN_EYES_CS_RIGHT  49
#define PIN_EYES_DC        48
#define PIN_EYES_RST       47

#endif // HARDWARE_DECLARATION_H
