#ifndef GENERAL_CONTROLLER_H
#define GENERAL_CONTROLLER_H

#include "ObserverPatternDelcaration.h"
#include "HardwareDeclaration.h"
#include "CommunicationPortocolDeclaration.h"

// ---------------------------------------------------------------------------
// GeneralController — base class for all hardware controllers.
// Inherits IObserver so every controller can be registered with the Coordinator.
// ---------------------------------------------------------------------------
class GeneralController : public IObserver
{
public:
    explicit GeneralController(const String &id);

    // Send a message over Serial (outbound to PC): "<id>:<message>"
    void sendToSerial(const String &message);

    // Subclasses must implement Update()
    virtual void Update(const String &message) override = 0;
    
    // Every controller should implement a sanity test
    virtual void sanityTest() = 0;

protected:
    // Subclasses override parseMessage() for payload-specific logic
    virtual void parseMessage(const String &message);
};

#endif // GENERAL_CONTROLLER_H
