#include "Coordinator.h"

Coordinator::Coordinator()
{
    _ledObservers.setStorage(_ledStorage,             MAX_LED_OBSERVERS,        0);
    _lcdObservers.setStorage(_lcdStorage,             MAX_LCD_OBSERVERS,        0);
    _buzzerObservers.setStorage(_buzzerStorage,       MAX_BUZZER_OBSERVERS,     0);
    _motorObservers.setStorage(_motorStorage,         MAX_MOTOR_OBSERVERS,      0);
    _ultrasoundObservers.setStorage(_ultrasoundStorage, MAX_ULTRASOUND_OBSERVERS, 0);
}

void Coordinator::Attach(IObserver *observer, const String &type)
{
    Vector<IObserver *> *list = listForType(type);
    if (list != nullptr && !list->full())
    {
        list->push_back(observer);
    }
}

void Coordinator::Detach(IObserver *observer, const String &type)
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

void Coordinator::Attach(IObserver *observer) { (void)observer; }
void Coordinator::Detach(IObserver *observer) { (void)observer; }

void Coordinator::Notify()
{
    notifyList(_ledObservers,        "BROADCAST");
    notifyList(_lcdObservers,        "BROADCAST");
    notifyList(_buzzerObservers,     "BROADCAST");
    notifyList(_motorObservers,      "BROADCAST");
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

void Coordinator::readAndRoute()
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

void Coordinator::printAllObservers() const
{
    Serial.println(F("=== LED ==="));       ListObservers(_ledObservers);
    Serial.println(F("=== LCD ==="));       ListObservers(_lcdObservers);
    Serial.println(F("=== BUZZER ==="));    ListObservers(_buzzerObservers);
    Serial.println(F("=== MOTOR ==="));     ListObservers(_motorObservers);
    Serial.println(F("=== ULTRASOUND ===")); ListObservers(_ultrasoundObservers);
}

Vector<IObserver *> *Coordinator::listForType(const String &type)
{
    if (type == "LED")  return &_ledObservers;
    if (type == "LCD")  return &_lcdObservers;
    if (type == "BUZZ") return &_buzzerObservers;
    if (type == "MOT")  return &_motorObservers;
    if (type == "US")   return &_ultrasoundObservers;
    return nullptr;
}

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
