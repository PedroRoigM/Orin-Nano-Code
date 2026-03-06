#include "BuzzerController.h"

BuzzerController::BuzzerController(const String &id, int pin)
    : GeneralController(id), _pin(pin)
{
    pinMode(_pin, OUTPUT);
}

void BuzzerController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    tone(_pin, 1000, 300); // 1 kHz for 300 ms
    delay(400);            // wait for tone to finish

    Serial.println(F("PASS"));
}

void BuzzerController::Update(const String &message)
{
    parseMessage(message);
}

void BuzzerController::parseMessage(const String &message)
{
    // The message format from Coordinator is "SPECIFIC_ID:COMMAND"
    // e.g. "BUZZ_1:SOUND:1000,500"
    int colonIndex = message.indexOf(':');
    if (colonIndex <= 0) return;

    String targetId = message.substring(0, colonIndex);
    String command  = message.substring(colonIndex + 1);

    // Only respond if the message is directed to this specific controller
    if (targetId != observerId) return;

    // Dispatch the command to the appropriate handler using protocol constants
    if (command == BUZZER_CMD_OFF) {
        handleCmdOff();
    }
    else if (command.startsWith(BUZZER_CMD_SOUND)) {
        handleCmdSound(command);
    }
}

void BuzzerController::handleCmdOff()
{
    noTone(_pin); // Stop the PWM signal on the buzzer pin
    
    // Feedback to Serial in format: BUZZ_<n>:STATE:OFF
    sendToSerial(String(BUZZER_STATE_PREFIX) + ":" + BUZZER_CMD_OFF);
}

void BuzzerController::handleCmdSound(const String &command)
{
    // Expected format: SOUND:<freq>,<duration_ms>
    // e.g. "SOUND:1000,500"
    int firstColon = command.indexOf(':');
    if (firstColon > 0) {
        String params = command.substring(firstColon + 1);
        int commaIndex = params.indexOf(',');
        
        if (commaIndex > 0) {
            long freq = params.substring(0, commaIndex).toInt();
            long duration = params.substring(commaIndex + 1).toInt();
            
            // Trigger tone if valid parameters are parsed
            if (freq > 0 && duration > 0) {
                tone(_pin, freq, duration);
                
                // Feedback to Serial in format: BUZZ_<n>:TONE:<freq>,<duration>
                sendToSerial(String(BUZZER_TONE_PREFIX) + ":" + String(freq) + "," + String(duration));
            }
        }
    }
}