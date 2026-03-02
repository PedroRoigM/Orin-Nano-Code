// UltrasoundController.ino
// Reads distance from an HC-SR04 ultrasonic sensor and sends it over Serial.
// Also registered as an IObserver so it can receive commands (e.g. "PING")
// via the coordinator's ultrasound list.
//
// Inbound message format: "PING" => triggers a single measurement

#include "ObserverPatternDelcaration.h"
#include "PinDeclaration.h"

class UltrasoundController : public GeneralController
{
public:
    /**
     * @param id      Human-readable name (e.g. "US_1")
     * @param pinTrig Trigger pin of the HC-SR04
     * @param pinEcho Echo pin of the HC-SR04
     */
    UltrasoundController(const String &id, int pinTrig, int pinEcho)
        : GeneralController(id), _pinTrig(pinTrig), _pinEcho(pinEcho)
    {
        pinMode(_pinTrig, OUTPUT);
        pinMode(_pinEcho, INPUT);
        digitalWrite(_pinTrig, LOW);
    }

    // -----------------------------------------------------------------------
    // measure() should be called periodically from loop() or on demand.
    // Sends result as "<id>:<distance_cm>" over Serial.
    // -----------------------------------------------------------------------
    void measure()
    {
        long distanceCm = readDistanceCm();

        String result = String(distanceCm);
        sendToSerial(result);
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
        // Other commands can be added here
    }

private:
    int _pinTrig;
    int _pinEcho;

    long readDistanceCm()
    {
        // Send a 10-microsecond HIGH pulse on the trigger pin
        digitalWrite(_pinTrig, LOW);
        delayMicroseconds(2);
        digitalWrite(_pinTrig, HIGH);
        delayMicroseconds(10);
        digitalWrite(_pinTrig, LOW);

        // Measure the echo pulse duration (timeout after 30 ms ~ 5 m)
        long duration = pulseIn(_pinEcho, HIGH, 30000UL);

        // Convert pulse duration to centimetres (speed of sound ~343 m/s)
        long distanceCm = duration / 58;
        return distanceCm;
    }
};
