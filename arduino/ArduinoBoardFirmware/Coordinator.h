#ifndef COORDINATOR_H
#define COORDINATOR_H

#include "ObserverPatternDelcaration.h"
#include "CommunicationPortocolDeclaration.h"
// ---------------------------------------------------------------------------
// Coordinator : ISubject
// Maintains one Vector<IObserver*> per controller type.
// readAndRoute() tokenises incoming serial messages and delegates to:
//   parseMessage()    — Serial I/O and tokenisation
//   isValidMessage()  — field validation and error reporting
//   dispatchCommand() — routing the command to the matching observer
// ---------------------------------------------------------------------------
class Coordinator : public ISubject
{
public:
    Coordinator();

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
    IObserver *_eyesStorage[MAX_EYES_OBSERVERS];

    Vector<IObserver *> _ledObservers;
    Vector<IObserver *> _lcdObservers;
    Vector<IObserver *> _buzzerObservers;
    Vector<IObserver *> _motorObservers;
    Vector<IObserver *> _ultrasoundObservers;
    Vector<IObserver *> _eyesObservers;

    Vector<IObserver *> *listForType(const String &type);
    void notifyList(Vector<IObserver *> &list, const String &message);

    // Non-blocking serial line accumulator (replaces Serial.readStringUntil)
    char    _rxBuf[128];
    uint8_t _rxLen;

    // readAndRoute() helpers
    bool parseMessage(const String &line, String &baseId, String &specificId, String &command);
    bool isValidMessage(const String &baseId, const String &specificId, const String &command);
    void dispatchCommand(const String &baseId, const String &specificId, const String &command);
};

#endif // COORDINATOR_H
