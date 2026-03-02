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
