#include "UltrasoundController.h"

UltrasoundController::UltrasoundController(const String &id, int pinTrig, int pinEcho)
    : GeneralController(id), _pinTrig(pinTrig), _pinEcho(pinEcho)
{
    pinMode(_pinTrig, OUTPUT);
    pinMode(_pinEcho, INPUT);
    digitalWrite(_pinTrig, LOW);
}

void UltrasoundController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    long distanceCm = readDistanceCm();

    if (distanceCm > 0)
    {
        Serial.print(F("PASS ("));
        Serial.print(distanceCm);
        Serial.println(F(" cm)"));
    }
    else
    {
        Serial.println(F("FAIL (no echo — check wiring)"));
    }
}

void UltrasoundController::measure()
{
    long distanceCm = readDistanceCm();
    sendToSerial(String(distanceCm));
}

void UltrasoundController::Update(const String &message)
{
    parseMessage(message);
}

void UltrasoundController::parseMessage(const String &message)
{
    if (message == "PING")
    {
        measure();
    }
}

long UltrasoundController::readDistanceCm()
{
    digitalWrite(_pinTrig, LOW);
    delayMicroseconds(2);
    digitalWrite(_pinTrig, HIGH);
    delayMicroseconds(10);
    digitalWrite(_pinTrig, LOW);

    long duration = pulseIn(_pinEcho, HIGH, 30000UL);
    return duration / 58;
}
