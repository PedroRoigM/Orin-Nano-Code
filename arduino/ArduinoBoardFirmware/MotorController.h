#ifndef MOTOR_CONTROLLER_H
#define MOTOR_CONTROLLER_H

#include "GeneralController.h"
#include "PinDeclaration.h"

// Observer for "MOT" messages.
// Message format: "<FWD|REV|STOP>,<speed 0-255>"
class MotorController : public GeneralController
{
public:
    MotorController(const String &id, int pinIn1, int pinIn2, int pinEn);

    void sanityTest();
    void Update(const String &message) override;

protected:
    void parseMessage(const String &message) override;

private:
    int _pinIn1, _pinIn2, _pinEn;

    void applyDirection(const String &direction, int speed);
    void stop();
};

#endif // MOTOR_CONTROLLER_H
