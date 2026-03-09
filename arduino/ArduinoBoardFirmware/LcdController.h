#ifndef LCD_CONTROLLER_H
#define LCD_CONTROLLER_H

#include "GeneralController.h"
#include <LiquidCrystal_I2C.h>

// Observer for "LCD" messages. Any string payload is displayed on the LCD.
// Requires: LiquidCrystal_I2C library (Library Manager)
class LcdController : public GeneralController
{
public:
    LcdController(const String &id, uint8_t address, uint8_t cols, uint8_t rows);

    void begin();
    void sanityTest();
    void Update(const String &message) override;

protected:
    void parseMessage(const String &message) override;

private:
    LiquidCrystal_I2C _lcd;

    // Applies a new text value to the LCD and reports over Serial.
    void displayText(const String &text);
};

#endif // LCD_CONTROLLER_H
