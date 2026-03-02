#ifndef BUZZER_CONTROLLER_H
#define BUZZER_CONTROLLER_H

#include "GeneralController.h"
#include "PinDeclaration.h"

// ---------------------------------------------------------------------------
// BuzzerController
// Observer for "BUZZ" messages.
// Message format: "<freq>,<duration_ms>"  or  "OFF"
// ---------------------------------------------------------------------------
class BuzzerController : public GeneralController
{
public:
    BuzzerController(const String &id, int pin)
        : GeneralController(id), _pin(pin)
    {
        pinMode(_pin, OUTPUT);
    }

    void Update(const String &message) override
    {
        parseMessage(message);
    }

protected:
    void parseMessage(const String &message) override
    {
        if (message == "OFF")
        {
            noTone(_pin);
            return;
        }

        int commaIndex = message.indexOf(',');
        if (commaIndex > 0)
        {
            long freq     = message.substring(0, commaIndex).toInt();
            long duration = message.substring(commaIndex + 1).toInt();
            if (freq > 0 && duration > 0)
            {
                tone(_pin, freq, duration);
            }
        }
    }

private:
    int _pin;
};

#endif // BUZZER_CONTROLLER_H
