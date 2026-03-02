// ObserverPattern.ino
// Implementations for IObserver and ISubject declared in ObserverPatternDelcaration.h

#include "ObserverPatternDelcaration.h"

// ---------------------------------------------------------------------------
// IObserver
// ---------------------------------------------------------------------------
IObserver::IObserver(const String &id)
{
    observerId = id;
}

String IObserver::getObserverId() const
{
    return observerId;
}

// ---------------------------------------------------------------------------
// ISubject
// ---------------------------------------------------------------------------
void ISubject::ListObservers(const Vector<IObserver *> &list) const
{
    Serial.print(F("Observers ("));
    Serial.print(list.size());
    Serial.println(F("):"));
    for (size_t i = 0; i < list.size(); i++)
    {
        if (list[i] != nullptr)
        {
            Serial.print(F("  ["));
            Serial.print(i);
            Serial.print(F("] "));
            Serial.println(list[i]->getObserverId());
        }
    }
}
