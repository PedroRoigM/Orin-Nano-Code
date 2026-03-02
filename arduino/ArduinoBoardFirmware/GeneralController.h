#ifndef GENERAL_CONTROLLER_H
#define GENERAL_CONTROLLER_H

#include "ObserverPatternDelcaration.h"

// ---------------------------------------------------------------------------
// GeneralController
// Base class for all hardware controllers. Inherits IObserver so every
// controller can be registered with the Coordinator.
// ---------------------------------------------------------------------------
class GeneralController : public IObserver
{
public:
    explicit GeneralController(const String &id)
        : IObserver(id)
    {
    }

    // Send a message over Serial (outbound to PC): "<id>:<message>"
    void sendToSerial(const String &message)
    {
        Serial.print(observerId);
        Serial.print(F(":"));
        Serial.println(message);
    }

    // Subclasses must implement Update()
    virtual void Update(const String &message) override = 0;

protected:
    // Subclasses can override parseMessage() for payload-specific logic
    virtual void parseMessage(const String &message)
    {
        (void)message; // no-op in base class
    }
};

#endif // GENERAL_CONTROLLER_H
