#ifndef ULTRASOUND_CONTROLLER_H
#define ULTRASOUND_CONTROLLER_H

#include "GeneralController.h"
#include "PinDeclaration.h"

// Observer for "US" messages. Also actively measures and reports distance.
// Message format: "PING" => triggers a single measurement
class UltrasoundController : public GeneralController
{
public:
    UltrasoundController(const String &id, int pinTrig, int pinEcho);

    void sanityTest();
    void measure();
    void Update(const String &message) override;

protected:
    void parseMessage(const String &message) override;

private:
    int _pinTrig;
    int _pinEcho;

    long readDistanceCm();
};

#endif // ULTRASOUND_CONTROLLER_H
