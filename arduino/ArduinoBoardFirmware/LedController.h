#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include "GeneralController.h"
#include "PinDeclaration.h"

// ---------------------------------------------------------------------------
// LedController
// Observer for "LED" messages. Messages: "ON", "OFF", "BLINK"
// ---------------------------------------------------------------------------
class LedController : public GeneralController
{
public:
    LedController(const String &id, int pin)
        : GeneralController(id), _pin(pin)
    {
        pinMode(_pin, OUTPUT);
        digitalWrite(_pin, LOW);
    }

    // -----------------------------------------------------------------------
    // sanityTest() — blinks the LED twice and reports result over Serial.
    // -----------------------------------------------------------------------
    void sanityTest()
    {
        Serial.print(F("[SanityTest] "));
        Serial.print(observerId);
        Serial.print(F(" ... "));

        for (int i = 0; i < 2; i++)
        {
            digitalWrite(_pin, HIGH);
            delay(150);
            digitalWrite(_pin, LOW);
            delay(150);
        }

        Serial.println(F("PASS"));
    }

    void Update(const String &message) override
    {
        parseMessage(message);
    }

protected:
    void parseMessage(const String &message) override
    {
        if (message == "ON")
        {
            digitalWrite(_pin, HIGH);
        }
        else if (message == "OFF")
        {
            digitalWrite(_pin, LOW);
        }
        else if (message == "BLINK")
        {
            digitalWrite(_pin, !digitalRead(_pin));
        }
    }

private:
    int _pin;
};

#endif // LED_CONTROLLER_H
