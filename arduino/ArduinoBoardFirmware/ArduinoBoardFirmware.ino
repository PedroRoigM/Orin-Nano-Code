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

// ---------------------------------------------------------------------------
// Hardware instances
// ---------------------------------------------------------------------------

LedController led1(LED_ID(1), PIN_LED_1, LED_NUM_PIXELS);
LedController led2(LED_ID(2), PIN_LED_2, LED_NUM_PIXELS);

// LcdController lcdExample("LCD_1", LCD_I2C_ADDRESS, LCD_COLS, LCD_ROWS);

BuzzerController buzzer1(BUZZER_ID(1), PIN_BUZZER_1);
BuzzerController buzzer2(BUZZER_ID(2), PIN_BUZZER_2);

// MotorController motorExample("MOT_1", PIN_MOTOR_1_IN1, PIN_MOTOR_1_IN2, PIN_MOTOR_1_EN);

// UltrasoundController us1(ULTRASOUND_ID(1), ULTRASOUND_1_TRIG_PIN, ULTRASOUND_1_ECHO_PIN);
// UltrasoundController us2(ULTRASOUND_ID(2), ULTRASOUND_2_TRIG_PIN, ULTRASOUND_2_ECHO_PIN);

EyeController eyeLeft(EYE_ID(1), PIN_EYES_CS_RIGHT, PIN_EYES_DC, PIN_EYES_RST, PIN_EYES_MOSI, PIN_EYES_SCK, false);
EyeController eyeRight(EYE_ID(2), PIN_EYES_CS_RIGHT, PIN_EYES_DC, PIN_EYES_RST, PIN_EYES_MOSI, PIN_EYES_SCK, false);

NeckController neck(NECK_ID(1), PIN_NECK_PAN, PIN_NECK_TILT);

// ---------------------------------------------------------------------------
// Coordinator
// ---------------------------------------------------------------------------
Coordinator coordinator;

// ---------------------------------------------------------------------------
// setup()
// ---------------------------------------------------------------------------
void setup()
{
    Serial.begin(115200);
    Wire.begin();

    coordinator.Attach(&led1);
    coordinator.Attach(&led2);

    // coordinator.Attach(&lcdExample);

    coordinator.Attach(&buzzer1);
    coordinator.Attach(&buzzer2);

    // coordinator.Attach(&motorExample);

    // coordinator.Attach(&us1);
    // coordinator.Attach(&us2);

    coordinator.Attach(&eyeLeft);
    coordinator.Attach(&eyeRight);

    coordinator.Attach(&neck);

    coordinator.printAllObservers();

    eyeLeft.begin();
    eyeRight.begin();

    // -----------------------------------------------------------------------
    // Sanity tests — exercise each controller once and report to Serial
    // -----------------------------------------------------------------------
    GeneralController* controllers[] = {
        &led1, &led2, &buzzer1, &buzzer2, &us1, &us2, &eyeLeft, &neck
    };
    int numControllers = sizeof(controllers) / sizeof(controllers[0]);

    sanityTest(controllers, numControllers);

    Serial.println(F("[Setup] Ready. Waiting for commands..."));
}

// ---------------------------------------------------------------------------
// loop()
// ---------------------------------------------------------------------------
void loop()
{
  
    coordinator.readAndRoute();

    eyeLeft.redraw();
    eyeRight.redraw();

    neck.loop();
}
