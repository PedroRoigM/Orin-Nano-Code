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

    _lcd.clear();
    _lcd.setCursor(0, 0);
    _lcd.print(F("Sanity Test OK"));
    delay(1000);
    _lcd.clear();

    Serial.println(F("PASS"));
}

void LcdController::Update(const String &message)
{
    parseMessage(message);
}

void LcdController::parseMessage(const String &message)
{
    _lcd.clear();
    _lcd.setCursor(0, 0);
    _lcd.print(message);
    sendToSerial("TEXT:" + message);
}
