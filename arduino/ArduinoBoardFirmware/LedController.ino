#include "LedController.h"

LedController::LedController(const String &id, int pin, int numPixels)
    : GeneralController(id), _pin(pin), _numPixels(numPixels),
      _strip(numPixels, pin, NEO_GRB + NEO_KHZ800),
      _r(255), _g(255), _b(255)
{
    _strip.begin();
}

void LedController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    // Red
    for (int i = 0; i < _numPixels; i++) _strip.setPixelColor(i, _strip.Color(255, 0, 0));
    _strip.show();
    delay(200);
    // Green
    for (int i = 0; i < _numPixels; i++) _strip.setPixelColor(i, _strip.Color(0, 255, 0));
    _strip.show();
    delay(200);
    // Blue
    for (int i = 0; i < _numPixels; i++) _strip.setPixelColor(i, _strip.Color(0, 0, 255));
    _strip.show();
    delay(200);
    // Off
    _strip.clear();
    _strip.show();

    Serial.println(F("PASS"));
}

void LedController::Update(const String &message)
{
    parseMessage(message);
}

void LedController::parseMessage(const String &message)
{
    int colonIndex = message.indexOf(':');
    if (colonIndex <= 0) return;

    String targetId = message.substring(0, colonIndex);
    String command  = message.substring(colonIndex + 1);

    if (targetId != observerId) return;

    if (command == LED_CMD_ON)
    {
        for (int i = 0; i < _numPixels; i++) _strip.setPixelColor(i, _strip.Color(_r, _g, _b));
        _strip.show();
        sendToSerial(String(LED_STATE_PREFIX) + ":" + LED_CMD_ON);
    }
    else if (command == LED_CMD_OFF)
    {
        _strip.clear();
        _strip.show();
        sendToSerial(String(LED_STATE_PREFIX) + ":" + LED_CMD_OFF);
    }
    else if (command.startsWith(LED_CMD_COLOR))
    {
        // Format: COLOR:r,g,b
        int firstComma = command.indexOf(':');
        if (firstComma > 0) {
            String colors = command.substring(firstComma + 1);
            int c1 = colors.indexOf(',');
            int c2 = colors.lastIndexOf(',');
            if (c1 > 0 && c2 > c1) {
                _r = colors.substring(0, c1).toInt();
                _g = colors.substring(c1 + 1, c2).toInt();
                _b = colors.substring(c2 + 1).toInt();
                
                for (int i = 0; i < _numPixels; i++) _strip.setPixelColor(i, _strip.Color(_r, _g, _b));
                _strip.show();
                sendToSerial(String(LED_COLOR_PREFIX) + ":" + String(_r) + "," + String(_g) + "," + String(_b));
            }
        }
    }
    else if (command == LED_CMD_RANDOM)
    {
        _r = boundColor(_r + random(-20, 21));
        _g = boundColor(_g + random(-20, 21));
        _b = boundColor(_b + random(-20, 21));
        
        for (int i = 0; i < _numPixels; i++) _strip.setPixelColor(i, _strip.Color(_r, _g, _b));
        _strip.show();
        sendToSerial(String(LED_COLOR_PREFIX) + ":" + String(_r) + "," + String(_g) + "," + String(_b));
    }
}

uint8_t LedController::boundColor(int value) {
    if (value < 0)   return 0;
    if (value > 255) return 255;
    return (uint8_t)value;
}