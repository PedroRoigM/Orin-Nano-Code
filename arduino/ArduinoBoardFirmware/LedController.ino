#include "LedController.h"

LedController::LedController(const String &id, int pin)
    : GeneralController(id), _pin(pin)
{
    pinMode(_pin, OUTPUT);
    digitalWrite(_pin, LOW);
}

void LedController::sanityTest()
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

void LedController::Update(const String &message)
{
    parseMessage(message);
}

void LedController::parseMessage(const String &message)
{
    if (message == "ON")
    {
        digitalWrite(_pin, HIGH);
        sendToSerial(F("STATE:ON"));
    }
    else if (message == "OFF")
    {
        digitalWrite(_pin, LOW);
        sendToSerial(F("STATE:OFF"));
    }
    else if (message == "BLINK")
    {
        digitalWrite(_pin, !digitalRead(_pin));
        sendToSerial(F("STATE:BLINK"));
    }
}