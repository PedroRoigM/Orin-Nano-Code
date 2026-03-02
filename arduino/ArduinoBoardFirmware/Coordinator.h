#ifndef COORDINATOR_H
#define COORDINATOR_H

#include "ObserverPatternDelcaration.h"

// ---------------------------------------------------------------------------
// Coordinator : ISubject
// Maintains one Vector<IObserver*> per controller type. Parses incoming serial
// messages ("<TYPE>:<payload>") and routes payloads to the matching list.
// ---------------------------------------------------------------------------
class Coordinator : public ISubject
{
public:
    Coordinator();

    // Typed Attach / Detach (preferred over the generic ISubject overrides)
    void Attach(IObserver *observer, const String &type);
    void Detach(IObserver *observer, const String &type);

    // ISubject interface (generic broadcast versions)
    void Attach(IObserver *observer) override;
    void Detach(IObserver *observer) override;
    void Notify() override;

    // Route message to one specific observer list
    void Notify(const String &type, const String &message);

    // Read one line from Serial and dispatch to the correct observer list
    void readAndRoute();

    // Print all registered observers to Serial (debug)
    void printAllObservers() const;

private:
    IObserver *_ledStorage[MAX_LED_OBSERVERS];
    IObserver *_lcdStorage[MAX_LCD_OBSERVERS];
    IObserver *_buzzerStorage[MAX_BUZZER_OBSERVERS];
    IObserver *_motorStorage[MAX_MOTOR_OBSERVERS];
    IObserver *_ultrasoundStorage[MAX_ULTRASOUND_OBSERVERS];

    Vector<IObserver *> _ledObservers;
    Vector<IObserver *> _lcdObservers;
    Vector<IObserver *> _buzzerObservers;
    Vector<IObserver *> _motorObservers;
    Vector<IObserver *> _ultrasoundObservers;

    Vector<IObserver *> *listForType(const String &type);
    void notifyList(Vector<IObserver *> &list, const String &message);
};

#endif // COORDINATOR_H
