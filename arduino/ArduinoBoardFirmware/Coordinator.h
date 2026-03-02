#ifndef COORDINATOR_H
#define COORDINATOR_H

#include "ObserverPatternDelcaration.h"
#include "LedController.h"
#include "LcdController.h"
#include "BuzzerController.h"
#include "MotorController.h"
#include "UltrasoundController.h"

// ---------------------------------------------------------------------------
// Coordinator : ISubject
// Maintains one Vector<IObserver*> per controller type (backed by fixed
// C-arrays) and routes incoming serial messages to the correct list.
//
// Serial protocol (9600 baud, newline-terminated):
//   "<TYPE>:<payload>\n"
//   Types: LED, LCD, BUZZ, MOT, US
// ---------------------------------------------------------------------------
class Coordinator : public ISubject
{
public:
    Coordinator()
    {
        _ledObservers.setStorage(_ledStorage,             MAX_LED_OBSERVERS,        0);
        _lcdObservers.setStorage(_lcdStorage,             MAX_LCD_OBSERVERS,        0);
        _buzzerObservers.setStorage(_buzzerStorage,       MAX_BUZZER_OBSERVERS,     0);
        _motorObservers.setStorage(_motorStorage,         MAX_MOTOR_OBSERVERS,      0);
        _ultrasoundObservers.setStorage(_ultrasoundStorage, MAX_ULTRASOUND_OBSERVERS, 0);
    }

    // ------------------------------------------------------------------
    // Typed Attach / Detach
    // ------------------------------------------------------------------

    /** Add an observer to the list matching 'type' ("LED","LCD","BUZZ","MOT","US"). */
    void Attach(IObserver *observer, const String &type)
    {
        Vector<IObserver *> *list = listForType(type);
        if (list != nullptr && !list->full())
        {
            list->push_back(observer);
        }
    }

    /** Remove an observer from the list matching 'type'. */
    void Detach(IObserver *observer, const String &type)
    {
        Vector<IObserver *> *list = listForType(type);
        if (list == nullptr) return;

        for (size_t i = 0; i < list->size(); i++)
        {
            if ((*list)[i] == observer)
            {
                list->remove(i);
                return;
            }
        }
    }

    // ------------------------------------------------------------------
    // ISubject interface (generic versions — use typed overloads above)
    // ------------------------------------------------------------------
    void Attach(IObserver *observer) override { (void)observer; }
    void Detach(IObserver *observer) override { (void)observer; }

    /** Broadcast to ALL observer lists. */
    void Notify() override
    {
        notifyList(_ledObservers,        "BROADCAST");
        notifyList(_lcdObservers,        "BROADCAST");
        notifyList(_buzzerObservers,     "BROADCAST");
        notifyList(_motorObservers,      "BROADCAST");
        notifyList(_ultrasoundObservers, "BROADCAST");
    }

    // ------------------------------------------------------------------
    // Typed Notify — sends message only to the matching list
    // ------------------------------------------------------------------
    void Notify(const String &type, const String &message)
    {
        Vector<IObserver *> *list = listForType(type);
        if (list != nullptr)
        {
            notifyList(*list, message);
        }
        else
        {
            Serial.print(F("[Coordinator] Unknown type: "));
            Serial.println(type);
        }
    }

    // ------------------------------------------------------------------
    // readAndRoute()
    // Call from loop(). Reads one '\n'-terminated line from Serial,
    // splits on ':', and dispatches payload to the matching observer list.
    // ------------------------------------------------------------------
    void readAndRoute()
    {
        if (!Serial.available()) return;

        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) return;

        int colonIndex = line.indexOf(':');
        if (colonIndex <= 0)
        {
            Serial.print(F("[Coordinator] Malformed: "));
            Serial.println(line);
            return;
        }

        String type    = line.substring(0, colonIndex);
        String payload = line.substring(colonIndex + 1);
        type.toUpperCase();

        Notify(type, payload);
    }

    // ------------------------------------------------------------------
    // Debug: print every registered observer to Serial
    // ------------------------------------------------------------------
    void printAllObservers() const
    {
        Serial.println(F("=== LED ==="));       ListObservers(_ledObservers);
        Serial.println(F("=== LCD ==="));       ListObservers(_lcdObservers);
        Serial.println(F("=== BUZZER ==="));    ListObservers(_buzzerObservers);
        Serial.println(F("=== MOTOR ==="));     ListObservers(_motorObservers);
        Serial.println(F("=== ULTRASOUND ===")); ListObservers(_ultrasoundObservers);
    }

private:
    // Per-type backing arrays
    IObserver *_ledStorage[MAX_LED_OBSERVERS];
    IObserver *_lcdStorage[MAX_LCD_OBSERVERS];
    IObserver *_buzzerStorage[MAX_BUZZER_OBSERVERS];
    IObserver *_motorStorage[MAX_MOTOR_OBSERVERS];
    IObserver *_ultrasoundStorage[MAX_ULTRASOUND_OBSERVERS];

    // Per-type Vectors
    Vector<IObserver *> _ledObservers;
    Vector<IObserver *> _lcdObservers;
    Vector<IObserver *> _buzzerObservers;
    Vector<IObserver *> _motorObservers;
    Vector<IObserver *> _ultrasoundObservers;

    Vector<IObserver *> *listForType(const String &type)
    {
        if (type == "LED")  return &_ledObservers;
        if (type == "LCD")  return &_lcdObservers;
        if (type == "BUZZ") return &_buzzerObservers;
        if (type == "MOT")  return &_motorObservers;
        if (type == "US")   return &_ultrasoundObservers;
        return nullptr;
    }

    void notifyList(Vector<IObserver *> &list, const String &message)
    {
        for (size_t i = 0; i < list.size(); i++)
        {
            if (list[i] != nullptr)
            {
                list[i]->Update(message);
            }
        }
    }
};

#endif // COORDINATOR_H
