#ifndef BUZZER_CONTROLLER_H
#define BUZZER_CONTROLLER_H

#include "GeneralController.h"

// Observer for "BUZZ" messages.
// Message format: "<freq>,<duration_ms>" or "OFF"
/**
 * @class BuzzerController
 * @brief Controller for piezoelectric buzzers.
 * 
 * Implements the communication protocol for the buzzer:
 * - Income:  BUZZ:BUZZ_<n>:OFF
 *            BUZZ:BUZZ_<n>:SOUND:<freq>,<duration_ms>
 * - Outcome: BUZZ_<n>:STATE:OFF
 *            BUZZ_<n>:TONE:<freq>,<duration_ms>
 */
class BuzzerController : public GeneralController
{
public:
    BuzzerController(const String &id, int pin);

    /**
     * @brief Performs a pass/fail startup test of the buzzer.
     */
    void sanityTest();

    /**
     * @brief IObserver implementation. Receives messages from the Coordinator.
     * @param message The raw message string (format: SPECIFIC_ID:COMMAND).
     */
    void Update(const String &message) override;

protected:
    /**
     * @brief Parses and dispatches the command payload.
     * @param message The message payload (format: SPECIFIC_ID:COMMAND).
     */
    void parseMessage(const String &message) override;

private:
    int _pin; ///< Hardware pin connected to the buzzer.

    /**
     * @brief Stops any current tone production.
     * Logic for BUZZER_CMD_OFF.
     */
    void handleCmdOff();

    /**
     * @brief Extracts frequency/duration and plays a tone.
     * @param command The sound command string (format: SOUND:<freq>,<duration>).
     */
    void handleCmdSound(const String &command);
};

#endif // BUZZER_CONTROLLER_H
