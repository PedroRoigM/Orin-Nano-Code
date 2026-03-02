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
