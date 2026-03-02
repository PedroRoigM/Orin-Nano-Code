// GeneralController.ino
// Base controller class. Inherits from IObserver to participate in the
// observer pattern. Provides shared serial send/receive utilities.

#include "ObserverPatternDelcaration.h"

class GeneralController : public IObserver
{
public:
    explicit GeneralController(const String &id)
        : IObserver(id)
    {
    }

    // -----------------------------------------------------------------------
    // Send a message over Serial (outbound to PC)
    // Format: "<observerId>:<message>\n"
    // -----------------------------------------------------------------------
    void sendToSerial(const String &message)
    {
        Serial.print(observerId);
        Serial.print(F(":"));
        Serial.println(message);
    }

    // -----------------------------------------------------------------------
    // Update() must be implemented by each concrete subclass.
    // -----------------------------------------------------------------------
    virtual void Update(const String &message) override = 0;

protected:
    // -----------------------------------------------------------------------
    // parseMessage() can be overridden to add per-controller payload parsing.
    // Called internally by Update() implementations if needed.
    // -----------------------------------------------------------------------
    virtual void parseMessage(const String &message)
    {
        // Base implementation: no-op
        // Subclasses override this to react to specific payload formats.
        (void)message;
    }
};