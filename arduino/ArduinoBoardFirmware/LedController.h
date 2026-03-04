#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include "GeneralController.h"
#include <Adafruit_NeoPixel.h>

// Observer for "LED" messages. Messages: "ON", "OFF", "COLOR:r,g,b", "RANDOM"
class LedController : public GeneralController
{
public:
    LedController(const String &id, int pin, int numPixels);

    void sanityTest();
    void Update(const String &message) override;

protected:
    void parseMessage(const String &message) override;

private:
    int _pin;
    int _numPixels;
    Adafruit_NeoPixel _strip;
    uint8_t _r, _g, _b;

    uint8_t boundColor(int value);
};

#endif // LED_CONTROLLER_H
