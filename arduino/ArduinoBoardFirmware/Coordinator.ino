#include "Coordinator.h"

Coordinator::Coordinator() : _rxLen(0)
{
    _ledObservers.setStorage(_ledStorage, MAX_LED_OBSERVERS, 0);
    _lcdObservers.setStorage(_lcdStorage, MAX_LCD_OBSERVERS, 0);
    _buzzerObservers.setStorage(_buzzerStorage, MAX_BUZZER_OBSERVERS, 0);
    _motorObservers.setStorage(_motorStorage, MAX_MOTOR_OBSERVERS, 0);
    _ultrasoundObservers.setStorage(_ultrasoundStorage, MAX_ULTRASOUND_OBSERVERS, 0);
    _eyesObservers.setStorage(_eyesStorage, MAX_EYES_OBSERVERS, 0);
}

void Coordinator::Attach(IObserver *observer)
{
    if (observer == nullptr) return;
    Vector<IObserver *> *list = listForType(observer->getObserverType());
    if (list != nullptr && !list->full())
    {
        list->push_back(observer);
    }
}

void Coordinator::Detach(IObserver *observer)
{
    if (observer == nullptr) return;
    Vector<IObserver *> *list = listForType(observer->getObserverType());
    if (list == nullptr)
        return;

    for (size_t i = 0; i < list->size(); i++)
    {
        if ((*list)[i] == observer)
        {
            list->remove(i);
            return;
        }
    }
}

void Coordinator::Notify()
{
    notifyList(_ledObservers, "BROADCAST");
    notifyList(_lcdObservers, "BROADCAST");
    notifyList(_buzzerObservers, "BROADCAST");
    notifyList(_motorObservers, "BROADCAST");
    notifyList(_ultrasoundObservers, "BROADCAST");
}

void Coordinator::Notify(const String &type, const String &message)
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

// ---------------------------------------------------------------------------
// readAndRoute()
//
// Non-blocking: consumes all available serial bytes into _rxBuf one char at
// a time (same approach as eyes_test.ino).  When a complete line ('\n' or
// '\r') is assembled it tokenises, validates and dispatches — then returns
// immediately so loop() can call eyeLeft.redraw() / eyeRight.redraw() on
// every iteration without being starved by a blocking readStringUntil().
//
// Protocol:  {BASE_ID}:{SPECIFIC_ID}:{COMMAND}   (newline-terminated)
// Examples:
//   EYE:EYE_1:DRAW:neutral,255,255,255,0,0,0
//   EYE:EYE_1:MOVE:30,-10
//   LED:LED_1:ON
//   BUZZ:BUZZ_1:SOUND:440,200
// ---------------------------------------------------------------------------
void Coordinator::readAndRoute()
{
    while (Serial.available())
    {
        char c = (char)Serial.read();

        if (c == '\n' || c == '\r')
        {
            if (_rxLen == 0)
                continue;   // blank line — skip

            _rxBuf[_rxLen] = '\0';
            String line(_rxBuf);
            _rxLen = 0;

            String baseId, specificId, command;
            if (!parseMessage(line, baseId, specificId, command))
                return;
            if (!isValidMessage(baseId, specificId, command))
                return;
            dispatchCommand(baseId, specificId, command);
            return;   // one command per call keeps loop() responsive
        }

        if (_rxLen < (uint8_t)(sizeof(_rxBuf) - 1))
            _rxBuf[_rxLen++] = c;
    }
}

// ---------------------------------------------------------------------------
// parseMessage()
//
// Tokenises an already-complete line into the three protocol fields.
// Returns false if the line is empty or malformed.
// (Serial reading is now handled by readAndRoute() non-blocking accumulator.)
// ---------------------------------------------------------------------------
bool Coordinator::parseMessage(const String &line, String &baseId, String &specificId, String &command)
{
    if (line.length() == 0)
        return false;

    int firstColon = line.indexOf(':');
    if (firstColon <= 0)
    {
        Serial.print(F("[Parse] Malformed (no base id): "));
        Serial.println(line);
        return false;
    }

    String rest = line.substring(firstColon + 1);   // "SPECIFIC_ID:COMMAND"
    int secondColon = rest.indexOf(':');
    if (secondColon <= 0)
    {
        Serial.print(F("[Parse] Malformed (no specific id): "));
        Serial.println(line);
        return false;
    }

    baseId     = line.substring(0, firstColon);
    baseId.toUpperCase();
    specificId = rest.substring(0, secondColon);
    command    = rest.substring(secondColon + 1);
    return true;
}

// ---------------------------------------------------------------------------
// isValidMessage()
//
// Validates that the parsed fields are non-empty and that the BASE_ID maps
// to a known observer list.  Prints a descriptive error for each failure.
// Returns false if any check fails.
// ---------------------------------------------------------------------------
bool Coordinator::isValidMessage(const String &baseId,
                                 const String &specificId,
                                 const String &command)
{
    if (baseId.length() == 0)
    {
        Serial.println(F("[Validate] Empty base id"));
        return false;
    }
    if (specificId.length() == 0)
    {
        Serial.println(F("[Validate] Empty specific id"));
        return false;
    }
    if (command.length() == 0)
    {
        Serial.println(F("[Validate] Empty command"));
        return false;
    }
    if (listForType(baseId) == nullptr)
    {
        Serial.print(F("[Validate] Unknown base id: "));
        Serial.println(baseId);
        return false;
    }
    return true;
}

// ---------------------------------------------------------------------------
// dispatchCommand()
//
// Looks up the observer list for BASE_ID and delivers COMMAND to the single
// observer whose id matches SPECIFIC_ID.  Reports if no match is found.
// ---------------------------------------------------------------------------
void Coordinator::dispatchCommand(const String &baseId,
                                  const String &specificId,
                                  const String &command)
{
    Vector<IObserver *> *list = listForType(baseId);
    if (list == nullptr)
    {
        Serial.print(F("[Dispatch] No observer for id: "));
        Serial.println(specificId);
    }

    notifyList(*list, String(specificId + ":" + command));
}

void Coordinator::printAllObservers() const
{
    Serial.println(F("=== LED ==="));
    ListObservers(_ledObservers);
    Serial.println(F("=== LCD ==="));
    ListObservers(_lcdObservers);
    Serial.println(F("=== BUZZER ==="));
    ListObservers(_buzzerObservers);
    Serial.println(F("=== MOTOR ==="));
    ListObservers(_motorObservers);
    Serial.println(F("=== ULTRASOUND ==="));
    ListObservers(_ultrasoundObservers);
    Serial.println(F("=== EYES ==="));
    ListObservers(_eyesObservers);
}

Vector<IObserver *> *Coordinator::listForType(const String &type)
{
    if (type == LED_BASE_ID)
        return &_ledObservers;
    if (type == LCD_BASE_ID)
        return &_lcdObservers;
    if (type == BUZZER_BASE_ID)
        return &_buzzerObservers;
    if (type == MOTOR_BASE_ID)
        return &_motorObservers;
    if (type == ULTRASOUND_BASE_ID)
        return &_ultrasoundObservers;
    if (type == EYE_BASE_ID)
        return &_eyesObservers;

    return nullptr;
}

// ---------------------------------------------------------------------------
// notifyList  — broadcast a message to every observer in the list
// ---------------------------------------------------------------------------
void Coordinator::notifyList(Vector<IObserver *> &list, const String &message)
{
    for (size_t i = 0; i < list.size(); i++)
    {
        if (list[i] != nullptr)
        {
            list[i]->Update(message);
        }
    }
}
