#include "LcdController.h"

LcdController::LcdController(const String &id, uint8_t address, uint8_t cols, uint8_t rows)
    : GeneralController(id, LCD_BASE_ID), _lcd(address, cols, rows)
{
}

void LcdController::begin()
{
    _lcd.init();
    _lcd.backlight();
    _lcd.clear();
}

void LcdController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    // Exercise the message pipeline by sending a text update as if it were
    // coming from the Coordinator.
    Update(observerId + ":Sanity Test OK");
    delay(1000);
    Update(observerId + ":");

    Serial.println(F("PASS"));
}

void LcdController::Update(const String &message)
{
    parseMessage(message);
}

void LcdController::parseMessage(const String &message)
{
    int colonIndex = message.indexOf(':');
    if (colonIndex <= 0) return;

    String targetId = message.substring(0, colonIndex);
    String text     = message.substring(colonIndex + 1);

    if (targetId != observerId) return;

    displayText(text);
}

void LcdController::displayText(const String &text)
{
    _lcd.clear();
    _lcd.setCursor(0, 0);
    _lcd.print(text);
    sendToSerial(String(LCD_TEXT_PREFIX) + ":" + text);
}
