#include "GeneralController.h"

GeneralController::GeneralController(const String &id)
    : IObserver(id)
{
}

void GeneralController::sendToSerial(const String &message)
{
    Serial.print(observerId);
    Serial.print(F(":"));
    Serial.println(message);
}

void GeneralController::parseMessage(const String &message)
{
    // Base implementation: no-op
    (void)message;
}