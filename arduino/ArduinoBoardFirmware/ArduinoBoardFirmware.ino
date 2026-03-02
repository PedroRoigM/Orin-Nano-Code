// ArduinoBoardFirmware.ino
// Main entry point.
//
// Serial protocol (9600 baud, newline-terminated):
//   LED:ON | LED:OFF | LED:BLINK
//   LCD:<text>
//   BUZZ:<freq>,<duration_ms> | BUZZ:OFF
//   MOT:FWD,<0-255> | MOT:REV,<0-255> | MOT:STOP,0
//   US:PING

#include "ControllerDeclaration.h"
#include "PinDeclaration.h"

// ---------------------------------------------------------------------------
// Hardware instances
// ---------------------------------------------------------------------------
LedController led1("LED_1", PIN_LED_1);
LedController led2("LED_2", PIN_LED_2);
LedController led3("LED_3", PIN_LED_3);

LcdController lcd1("LCD_1", LCD_I2C_ADDRESS, LCD_COLS, LCD_ROWS);
LcdController lcd2("LCD_2", LCD_I2C_ADDRESS, LCD_COLS, LCD_ROWS);
LcdController lcd3("LCD_3", LCD_I2C_ADDRESS, LCD_COLS, LCD_ROWS);

BuzzerController    buzzer1("BUZZ_1", PIN_BUZZER);
MotorController     motor1("MOT_1",  PIN_MOTOR_1_IN1, PIN_MOTOR_1_IN2, PIN_MOTOR_1_EN);
UltrasoundController us1("US_1",    PIN_ULTRASOUND_TRIG, PIN_ULTRASOUND_ECHO);

// ---------------------------------------------------------------------------
// Coordinator
// ---------------------------------------------------------------------------
Coordinator coordinator;

// ---------------------------------------------------------------------------
// setup()
// ---------------------------------------------------------------------------
void setup()
{
    Serial.begin(9600);
    while (!Serial) { };

    coordinator.Attach(&led1,    "LED");
    coordinator.Attach(&led2,    "LED");
    coordinator.Attach(&led3,    "LED");

    coordinator.Attach(&lcd1,    "LCD");
    coordinator.Attach(&lcd2,    "LCD");
    coordinator.Attach(&lcd3,    "LCD");

    coordinator.Attach(&buzzer1, "BUZZ");
    coordinator.Attach(&motor1,  "MOT");
    coordinator.Attach(&us1,     "US");

    coordinator.printAllObservers();

    // -----------------------------------------------------------------------
    // Sanity tests — exercise each controller once and report to Serial
    // -----------------------------------------------------------------------
    Serial.println(F("========== SANITY TESTS =========="));

    led1.sanityTest();
    led2.sanityTest();
    led3.sanityTest();

    lcd1.sanityTest();
    lcd2.sanityTest();
    lcd3.sanityTest();

    buzzer1.sanityTest();

    motor1.sanityTest();

    us1.sanityTest();

    Serial.println(F("========== TESTS COMPLETE =========="));
    Serial.println(F("[Setup] Ready. Waiting for commands..."));
}

// ---------------------------------------------------------------------------
// loop()
// ---------------------------------------------------------------------------
void loop()
{
    coordinator.readAndRoute();

    // Periodic ultrasound measurement every 500 ms
    static unsigned long lastMeasure = 0;
    unsigned long now = millis();
    if (now - lastMeasure >= 500)
    {
        lastMeasure = now;
        us1.measure();
    }
}
