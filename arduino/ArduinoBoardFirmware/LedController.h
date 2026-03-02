#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include "GeneralController.h"
#include "PinDeclaration.h"

// Observer for "LED" messages. Messages: "ON", "OFF", "BLINK"
class LedController : public GeneralController
{
public:
    LedController(const String &id, int pin);

    void sanityTest();
    void Update(const String &message) override;

protected:
    void parseMessage(const String &message) override;

private:
    int _pin;
};

#endif // LED_CONTROLLER_H
