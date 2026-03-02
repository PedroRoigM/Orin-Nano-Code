#ifndef ULTRASOUND_CONTROLLER_H
#define ULTRASOUND_CONTROLLER_H

#include "GeneralController.h"
#include "PinDeclaration.h"

// ---------------------------------------------------------------------------
// UltrasoundController
// Observer for "US" messages. Also actively measures and reports distance.
// Message format: "PING"  => triggers a single measurement
// ---------------------------------------------------------------------------
class UltrasoundController : public GeneralController
{
public:
    UltrasoundController(const String &id, int pinTrig, int pinEcho)
        : GeneralController(id), _pinTrig(pinTrig), _pinEcho(pinEcho)
    {
        pinMode(_pinTrig, OUTPUT);
        pinMode(_pinEcho, INPUT);
        digitalWrite(_pinTrig, LOW);
    }

    // Call periodically from loop() to send distance readings to the PC
    void measure()
    {
        long distanceCm = readDistanceCm();
        sendToSerial(String(distanceCm));
    }

    void Update(const String &message) override
    {
        parseMessage(message);
    }

protected:
    void parseMessage(const String &message) override
    {
        if (message == "PING")
        {
            measure();
        }
    }

private:
    int _pinTrig;
    int _pinEcho;

    long readDistanceCm()
    {
        digitalWrite(_pinTrig, LOW);
        delayMicroseconds(2);
        digitalWrite(_pinTrig, HIGH);
        delayMicroseconds(10);
        digitalWrite(_pinTrig, LOW);

        // Timeout at 30 000 µs ≈ 5 m range
        long duration = pulseIn(_pinEcho, HIGH, 30000UL);
        return duration / 58;
    }
};

#endif // ULTRASOUND_CONTROLLER_H
