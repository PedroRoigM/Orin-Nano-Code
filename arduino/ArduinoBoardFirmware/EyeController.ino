#include "EyeController.h"

EyeController::EyeController(const String &id, int pinCs, int pinDc, int pinRst, bool mirrored)
    : GeneralController(id),
      _disp(pinCs, pinDc, -1),
      _pinRst(pinRst),
      _mirrored(mirrored),
      _irisColor(rgb888to565(180, 180, 200)), // Soft blue/white
      _gazeX(0), _gazeY(0),
      _squint(0), _wide(0),
      _needRedraw(true)
{
    // Note: hardwareReset should be called by the first eye or once in setup
    // But for safety in standalone usage:
    hardwareReset(_pinRst);
    _disp.begin();
    _disp.fillScreen(0x0000);
}

void EyeController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    const uint16_t colors[] = {0xF800, 0x07E0, 0x001F};
    for (uint16_t c : colors)
    {
        _disp.fillScreen(c);
        delay(150);
    }
    
    _needRedraw = true;
    redraw();

    Serial.println(F("PASS"));
}

void EyeController::Update(const String &message)
{
    parseMessage(message);
}

void EyeController::parseMessage(const String &message)
{
    int colonIndex = message.indexOf(':');
    if (colonIndex <= 0) return;

    String targetId = message.substring(0, colonIndex);
    String payload  = message.substring(colonIndex + 1);

    if (targetId != observerId) return;

    if (payload.length() == 0) return;

    char first = payload.charAt(0);
    if (first == '-' || isDigit(first))
        parseGaze(payload);
    else
        parseEyes(payload);
}

void EyeController::parseEyes(const String &payload)
{
    int i0 = payload.indexOf(',');
    if (i0 < 0) return;

    int i1 = payload.indexOf(',', i0 + 1);
    int i2 = payload.indexOf(',', i1 + 1);
    int i3 = payload.indexOf(',', i2 + 1);
    int i4 = payload.indexOf(',', i3 + 1);
    if (i1 < 0 || i2 < 0 || i3 < 0 || i4 < 0) return;

    uint8_t r = (uint8_t)payload.substring(i0 + 1, i1).toInt();
    uint8_t g = (uint8_t)payload.substring(i1 + 1, i2).toInt();
    uint8_t b = (uint8_t)payload.substring(i2 + 1, i3).toInt();
    int squint = (int)payload.substring(i3 + 1, i4).toInt();
    int wide = (int)payload.substring(i4 + 1).toInt();

    _irisColor = rgb888to565(r, g, b);
    _squint = constrain(squint, 0, 100);
    _wide = constrain(wide, 0, 100);
    _needRedraw = true;

    sendToSerial(F("IRIS:ok"));
}

void EyeController::parseGaze(const String &payload)
{
    int comma = payload.indexOf(',');
    if (comma < 0) return;

    int gx = payload.substring(0, comma).toInt();
    int gy = payload.substring(comma + 1).toInt();

    _gazeX = constrain(gx * (int)EYE_GAZE_MAX / 100, -(int)EYE_GAZE_MAX, (int)EYE_GAZE_MAX);
    _gazeY = constrain(gy * (int)EYE_GAZE_MAX / 100, -(int)EYE_GAZE_MAX, (int)EYE_GAZE_MAX);
    _needRedraw = true;

    sendToSerial(F("GAZE:ok"));
}

void EyeController::redraw()
{
    if (!_needRedraw) return;
    _needRedraw = false;
    drawEye();
}

void EyeController::drawEye()
{
    const uint16_t BLACK = 0x0000;
    const uint16_t WHITE = 0xFFFF;

    int gx = _mirrored ? -_gazeX : _gazeX;
    int gy = _gazeY;

    _disp.fillScreen(BLACK);
    _disp.fillCircle(EYE_CX, EYE_CY, EYE_SCLERA_R, WHITE);

    int irisCX = EYE_CX + gx;
    int irisCY = EYE_CY + gy;

    float dist = sqrt((float)(gx * gx + gy * gy));
    float maxDist = (float)(EYE_SCLERA_R - EYE_IRIS_R - 3);
    if (dist > 0.5f && dist > maxDist)
    {
        irisCX = EYE_CX + (int)(gx * maxDist / dist);
        irisCY = EYE_CY + (int)(gy * maxDist / dist);
    }
    _disp.fillCircle(irisCX, irisCY, EYE_IRIS_R, _irisColor);
    _disp.fillCircle(irisCX, irisCY, EYE_PUPIL_R, BLACK);
    _disp.fillCircle(irisCX - EYE_IRIS_R / 4, irisCY - EYE_IRIS_R / 4, EYE_IRIS_R / 6, WHITE);

    if (_squint > 0)
    {
        int eyelidH = (_squint * (int)EYE_SCLERA_R) / 100;
        _disp.fillRect(0, EYE_CY - EYE_SCLERA_R, 240, eyelidH, BLACK);
    }
}

uint16_t EyeController::rgb888to565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((uint16_t)(r & 0xF8) << 8) | ((uint16_t)(g & 0xFC) << 3) | ((uint16_t)(b >> 3));
}

void EyeController::hardwareReset(int pin)
{
    pinMode(pin, OUTPUT);
    digitalWrite(pin, HIGH);
    delay(10);
    digitalWrite(pin, LOW);
    delay(20);
    digitalWrite(pin, HIGH);
    delay(150);
}
