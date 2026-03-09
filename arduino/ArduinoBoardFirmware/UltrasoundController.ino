#include "UltrasoundController.h"

UltrasoundController::UltrasoundController(const String &id, int pinTrig, int pinEcho)
    : GeneralController(id, ULTRASOUND_BASE_ID), _pinTrig(pinTrig), _pinEcho(pinEcho)
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

    // First, exercise the message pipeline with a protocol-style ping.
    Update(observerId + ":" + String(ULTRASOUND_PING_COMMAND));

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
    if (distanceCm > 0)
    {
        sendToSerial(String(ULTRASOUND_DISTANCE_MEASURED_PREFIX) + ":" + String(distanceCm));
    }
    else
    {
        sendToSerial(String(ULTRASOUND_DISTANCE_MEASURED_PREFIX) + ":" + String(ERROR_MESSAGE));
    }
}

// ---------------------------------------------------------------------------
// Update()
//
// Called by the Coordinator with a message in the form:
//   {SPECIFIC_ID}:{COMMAND}      e.g.  "US_1:PING"
//
// The Coordinator broadcasts to every observer in the US list, so we must
// check that the SPECIFIC_ID matches our own observerId before acting.
// ---------------------------------------------------------------------------
void UltrasoundController::Update(const String &message)
{
    parseMessage(message);
}

// ---------------------------------------------------------------------------
// parseMessage()
//
// Splits "{SPECIFIC_ID}:{COMMAND}" and acts only when:
//   1. The SPECIFIC_ID matches this controller's observerId, AND
//   2. The COMMAND is ULTRASOUND_PING_COMMAND ("PING")
// ---------------------------------------------------------------------------
void UltrasoundController::parseMessage(const String &message)
{
    int colonIndex = message.indexOf(':');
    if (colonIndex <= 0)
        return;

    String targetId = message.substring(0, colonIndex);
    String command  = message.substring(colonIndex + 1);

    if (targetId != observerId)
        return;

    if (command == ULTRASOUND_PING_COMMAND)
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
