#ifndef MOTOR_CONTROLLER_H
#define MOTOR_CONTROLLER_H

#include "GeneralController.h"
#include "PinDeclaration.h"

// ---------------------------------------------------------------------------
// MotorController
// Observer for "MOT" messages.
// Message format: "<FWD|REV|STOP>,<speed 0-255>"
// ---------------------------------------------------------------------------
class MotorController : public GeneralController
{
public:
    MotorController(const String &id, int pinIn1, int pinIn2, int pinEn)
        : GeneralController(id), _pinIn1(pinIn1), _pinIn2(pinIn2), _pinEn(pinEn)
    {
        pinMode(_pinIn1, OUTPUT);
        pinMode(_pinIn2, OUTPUT);
        pinMode(_pinEn, OUTPUT);
        stop();
    }

    // -----------------------------------------------------------------------
    // sanityTest() — runs the motor briefly forward then stops, reports to Serial.
    // -----------------------------------------------------------------------
    void sanityTest()
    {
        Serial.print(F("[SanityTest] "));
        Serial.print(observerId);
        Serial.print(F(" ... "));

        // Forward at low speed for 500 ms
        digitalWrite(_pinIn1, HIGH);
        digitalWrite(_pinIn2, LOW);
        analogWrite(_pinEn, 80);
        delay(500);
        stop();

        Serial.println(F("PASS"));
    }

    void Update(const String &message) override
    {
        parseMessage(message);
    }

protected:
    void parseMessage(const String &message) override
    {
        int commaIndex = message.indexOf(',');
        if (commaIndex < 0)
        {
            applyDirection(message, 0);
            return;
        }

        String direction = message.substring(0, commaIndex);
        int speed        = constrain(message.substring(commaIndex + 1).toInt(), 0, 255);
        applyDirection(direction, speed);
    }

private:
    int _pinIn1, _pinIn2, _pinEn;

    void applyDirection(const String &direction, int speed)
    {
        if (direction == "FWD")
        {
            digitalWrite(_pinIn1, HIGH);
            digitalWrite(_pinIn2, LOW);
            analogWrite(_pinEn, speed);
        }
        else if (direction == "REV")
        {
            digitalWrite(_pinIn1, LOW);
            digitalWrite(_pinIn2, HIGH);
            analogWrite(_pinEn, speed);
        }
        else
        {
            stop();
        }
    }

    void stop()
    {
        digitalWrite(_pinIn1, LOW);
        digitalWrite(_pinIn2, LOW);
        analogWrite(_pinEn, 0);
    }
};

#endif // MOTOR_CONTROLLER_H
