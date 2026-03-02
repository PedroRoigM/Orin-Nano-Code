#ifndef LCD_CONTROLLER_H
#define LCD_CONTROLLER_H

#include "GeneralController.h"
#include "PinDeclaration.h"
#include <LiquidCrystal_I2C.h>

// ---------------------------------------------------------------------------
// LcdController
// Observer for "LCD" messages. Any string payload is displayed on the LCD.
// Requires: LiquidCrystal_I2C library (Library Manager)
// ---------------------------------------------------------------------------
class LcdController : public GeneralController
{
public:
    LcdController(const String &id, uint8_t address, uint8_t cols, uint8_t rows)
        : GeneralController(id), _lcd(address, cols, rows)
    {
        _lcd.init();
        _lcd.backlight();
        _lcd.clear();
    }

    // -----------------------------------------------------------------------
    // sanityTest() — writes a test string to the LCD and reports to Serial.
    // -----------------------------------------------------------------------
    void sanityTest()
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

    void Update(const String &message) override
    {
        parseMessage(message);
    }

protected:
    void parseMessage(const String &message) override
    {
        _lcd.clear();
        _lcd.setCursor(0, 0);
        _lcd.print(message);
    }

private:
    LiquidCrystal_I2C _lcd;
};

#endif // LCD_CONTROLLER_H
