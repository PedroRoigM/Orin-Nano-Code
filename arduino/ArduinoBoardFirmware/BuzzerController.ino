#include "BuzzerController.h"

BuzzerController::BuzzerController(const String &id, int pin)
    : GeneralController(id), _pin(pin)
{
    pinMode(_pin, OUTPUT);
}

void BuzzerController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    tone(_pin, 1000, 300); // 1 kHz for 300 ms
    delay(400);            // wait for tone to finish

    Serial.println(F("PASS"));
}

void BuzzerController::Update(const String &message)
{
    parseMessage(message);
}

void BuzzerController::parseMessage(const String &message)
{
    if (message == "OFF")
    {
        noTone(_pin);
        sendToSerial(F("STATE:OFF"));
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
            sendToSerial("TONE:" + String(freq) + "," + String(duration));
        }
    }
}
