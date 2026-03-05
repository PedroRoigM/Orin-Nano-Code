#ifndef BUZZER_CONTROLLER_H
#define BUZZER_CONTROLLER_H

#include "GeneralController.h"

// Observer for "BUZZ" messages.
// Message format: "<freq>,<duration_ms>" or "OFF"
class BuzzerController : public GeneralController
{
public:
    BuzzerController(const String &id, int pin);

    void sanityTest();
    void Update(const String &message) override;

protected:
    void parseMessage(const String &message) override;

private:
    int _pin;
};

#endif // BUZZER_CONTROLLER_H
