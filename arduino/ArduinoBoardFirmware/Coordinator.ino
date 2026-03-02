// Coordinator.ino
// The Coordinator acts as the ISubject. It maintains one Vector<IObserver*>
// per controller type, each backed by a fixed-size C-array to avoid dynamic
// allocation on Arduino hardware.
//
// Serial message protocol:
//   "<TYPE>:<payload>\n"
//   Types: LED, LCD, BUZZ, MOT, US
//   Example: "LED:ON"  "LCD:Hello!"  "BUZZ:1000,300"  "MOT:FWD,180"  "US:PING"

#include "ObserverPatternDelcaration.h"

class Coordinator : public ISubject
{
public:

    Coordinator()
    {
        // Bind each Vector to its pre-allocated backing array
        _ledObservers.setStorage(_ledStorage, MAX_LED_OBSERVERS, 0);
        _lcdObservers.setStorage(_lcdStorage, MAX_LCD_OBSERVERS, 0);
        _buzzerObservers.setStorage(_buzzerStorage, MAX_BUZZER_OBSERVERS, 0);
        _motorObservers.setStorage(_motorStorage, MAX_MOTOR_OBSERVERS, 0);
        _ultrasoundObservers.setStorage(_ultrasoundStorage, MAX_ULTRASOUND_OBSERVERS, 0);
    }

    // -----------------------------------------------------------------------
    // Typed Attach / Detach
    // -----------------------------------------------------------------------

    /**
     * @brief Attach an observer to the list matching the given type string.
     * @param observer Pointer to the observer to add.
     * @param type     One of: "LED", "LCD", "BUZZ", "MOT", "US"
     */
    void Attach(IObserver *observer, const String &type)
    {
        Vector<IObserver *> *list = listForType(type);
        if (list != nullptr && !list->full())
        {
            list->push_back(observer);
        }
    }

    /**
     * @brief Detach an observer from the list matching the given type string.
     */
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

    // -----------------------------------------------------------------------
    // ISubject interface overrides (generic / broadcast versions)
    // -----------------------------------------------------------------------

    /** Generic Attach — required by ISubject but not used directly. */
    void Attach(IObserver *observer) override
    {
        (void)observer;
        // Use the typed Attach(observer, type) overload instead.
    }

    /** Generic Detach — required by ISubject but not used directly. */
    void Detach(IObserver *observer) override
    {
        (void)observer;
        // Use the typed Detach(observer, type) overload instead.
    }

    /** Broadcast a message to ALL observer lists. */
    void Notify() override
    {
        NotifyList(_ledObservers, "BROADCAST");
        NotifyList(_lcdObservers, "BROADCAST");
        NotifyList(_buzzerObservers, "BROADCAST");
        NotifyList(_motorObservers, "BROADCAST");
        NotifyList(_ultrasoundObservers, "BROADCAST");
    }

    // -----------------------------------------------------------------------
    // Typed Notify — routes a message to one specific observer list
    // -----------------------------------------------------------------------
    void Notify(const String &type, const String &message)
    {
        Vector<IObserver *> *list = listForType(type);
        if (list != nullptr)
        {
            NotifyList(*list, message);
        }
        else
        {
            Serial.print(F("[Coordinator] Unknown type: "));
            Serial.println(type);
        }
    }

    // -----------------------------------------------------------------------
    // readAndRoute()
    // Call this from loop(). Reads one complete line from Serial, parses the
    // "<TYPE>:<payload>" format, and routes the payload to the correct list.
    // -----------------------------------------------------------------------
    void readAndRoute()
    {
        if (!Serial.available()) return;

        String line = Serial.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) return;

        // Find the colon separator
        int colonIndex = line.indexOf(':');
        if (colonIndex <= 0)
        {
            Serial.print(F("[Coordinator] Malformed message: "));
            Serial.println(line);
            return;
        }

        String type    = line.substring(0, colonIndex);
        String payload = line.substring(colonIndex + 1);

        type.toUpperCase();
        Notify(type, payload);
    }

    // -----------------------------------------------------------------------
    // Debug helpers
    // -----------------------------------------------------------------------
    void printAllObservers() const
    {
        Serial.println(F("=== LED observers ==="));
        ListObservers(_ledObservers);
        Serial.println(F("=== LCD observers ==="));
        ListObservers(_lcdObservers);
        Serial.println(F("=== BUZZER observers ==="));
        ListObservers(_buzzerObservers);
        Serial.println(F("=== MOTOR observers ==="));
        ListObservers(_motorObservers);
        Serial.println(F("=== ULTRASOUND observers ==="));
        ListObservers(_ultrasoundObservers);
    }

private:
    // -----------------------------------------------------------------------
    // Per-type backing storage arrays + Vectors
    // -----------------------------------------------------------------------
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

    // -----------------------------------------------------------------------
    // Returns a pointer to the correct observer list for the given type tag.
    // Returns nullptr if the type is unrecognised.
    // -----------------------------------------------------------------------
    Vector<IObserver *> *listForType(const String &type)
    {
        if (type == "LED")  return &_ledObservers;
        if (type == "LCD")  return &_lcdObservers;
        if (type == "BUZZ") return &_buzzerObservers;
        if (type == "MOT")  return &_motorObservers;
        if (type == "US")   return &_ultrasoundObservers;
        return nullptr;
    }

    // Notify every observer in a list with the given message
    void NotifyList(Vector<IObserver *> &list, const String &message)
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
