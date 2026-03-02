#ifndef OBSERVER_PATTERN_DECLARATION_H
#define OBSERVER_PATTERN_DECLARATION_H

#include <Arduino.h>
#include <Vector.h>

// ---------------------------------------------------------------------------
// Per-type maximum observer counts (adjust per hardware configuration)
// ---------------------------------------------------------------------------
#define MAX_LED_OBSERVERS         10
#define MAX_LCD_OBSERVERS         10
#define MAX_BUZZER_OBSERVERS      10
#define MAX_MOTOR_OBSERVERS       10
#define MAX_ULTRASOUND_OBSERVERS  10

// ---------------------------------------------------------------------------
// IObserver
// ---------------------------------------------------------------------------
/**
 * @brief Interface for all observer controllers.
 *
 * Each concrete controller (LED, LCD, Buzzer, Motor, Ultrasound) must
 * inherit from this class and implement Update() to receive routed messages.
 */
class IObserver
{
public:
    /**
     * @param observerId Human-readable identifier for this observer instance.
     */
    explicit IObserver(const String &observerId);

    virtual ~IObserver() {}

    /**
     * @brief Called by the Coordinator when a message is routed to this observer.
     * @param message Payload extracted from the serial message.
     */
    virtual void Update(const String &message) = 0;

    /** @brief Returns this observer's identifier. */
    String getObserverId() const;

protected:
    String observerId;
};

// ---------------------------------------------------------------------------
// ISubject
// ---------------------------------------------------------------------------
/**
 * @brief Base interface for subjects (the Coordinator).
 *
 * The Coordinator maintains separate Vector<IObserver*> lists per controller
 * type, backed by fixed-size C-arrays (size defined by MAX_*_OBSERVERS).
 * This avoids dynamic allocation on constrained Arduino hardware.
 */
class ISubject
{
public:
    virtual ~ISubject() {}

    /** @brief Attach an observer. */
    virtual void Attach(IObserver *observer) = 0;

    /** @brief Detach an observer. */
    virtual void Detach(IObserver *observer) = 0;

    /**
     * @brief Notify all attached observers (broadcast).
     * Concrete subjects may also provide typed Notify overloads.
     */
    virtual void Notify() = 0;

    /**
     * @brief Prints the list of attached observers to Serial.
     * Implemented in ObserverPattern.ino.
     */
    virtual void ListObservers(const Vector<IObserver *> &list) const;
};

#endif // OBSERVER_PATTERN_DECLARATION_H
