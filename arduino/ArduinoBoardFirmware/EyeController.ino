#include "EyeController.h"
#include <math.h>
#include <SPI.h>

// ─── Constructor ─────────────────────────────────────────────────────────────
EyeController::EyeController(const String &id,
                             int pinCs, int pinDc, int pinRst,
                             int pinMosi, int pinSclk)
    : GeneralController(id, EYE_BASE_ID),
      _pinCs(pinCs), _pinDc(pinDc), _pinRst(pinRst),
      _pinMosi(pinMosi), _pinSclk(pinSclk),
      _on(false),
      _showEye(false),
      _r(255), _g(255), _b(255),
      _bgR(0), _bgG(0), _bgB(0),
      _gx(0), _gy(0),
      _fCx(EYE_CX), _fCy(EYE_CY),
      _dCx(EYE_CX), _dCy(EYE_CY),
      _dR(0), _dG(0), _dB(0),
      _dBgR(1), _dBgG(0), _dBgB(0), // differs from _bgR/G/B → forces first draw
      _dirty(false)
{
    // Pre-compute the capsule half-width per row
    for (int ady = 0; ady < EYE_SPAN_SIZE; ady++)
    {
        if (ady <= EYE_Y_FLAT)
        {
            _eyeSpan[ady] = EYE_R;
        }
        else
        {
            long dy = ady - EYE_Y_FLAT;
            long dy2 = dy * dy;
            _eyeSpan[ady] = (dy2 > EYE_R2) ? 0
                                           : (uint8_t)sqrtf((float)(EYE_R2 - dy2));
        }
    }
}

// ─── begin ───────────────────────────────────────────────────────────────────
void EyeController::begin()
{
    pinMode(_pinRst, OUTPUT);
    pinMode(_pinCs, OUTPUT);
    pinMode(_pinDc, OUTPUT);
    pinMode(_pinMosi, OUTPUT);
    pinMode(_pinSclk, OUTPUT);

    csHigh();
    dcHigh();

    SPI.begin();
    SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));

    initGC9A01();
    fillScreen(rgb565(_bgR, _bgG, _bgB));

    // Output: EYE_<n>:READY:ok
    sendToSerial(String(EYE_READY_PREFIX) + ":ok");
    _on = true;
}

// ─── sanityTest ──────────────────────────────────────────────────────────────
void EyeController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    // FILL: solid red
    Update(observerId + ":" + EYE_CMD_FILL + ":255,0,0");
    delay(400);

    // FILL: solid green
    Update(observerId + ":" + EYE_CMD_FILL + ":0,255,0");
    delay(400);

    // FILL: solid blue
    Update(observerId + ":" + EYE_CMD_FILL + ":0,0,255");
    delay(400);

    // DRAW: white eye on black background, centred
    Update(observerId + ":" + EYE_CMD_DRAW + ":neutral,255,255,255,0,0,0");
    redraw();
    delay(400);

    // MOVE: look right
    Update(observerId + ":" + EYE_CMD_MOVE + ":80,0");
    redraw();
    delay(300);

    // MOVE: look left
    Update(observerId + ":" + EYE_CMD_MOVE + ":-80,0");
    redraw();
    delay(300);

    // MOVE: centre
    Update(observerId + ":" + EYE_CMD_MOVE + ":0,0");
    redraw();
    delay(300);

    // OFF / ON cycle
    Update(observerId + ":" + EYE_CMD_OFF);
    delay(200);
    Update(observerId + ":" + EYE_CMD_ON);

    Serial.println(F("PASS"));
}

// ─── Update ──────────────────────────────────────────────────────────────────
void EyeController::Update(const String &message)
{
    parseMessage(message);
}

// ─── parseMessage ─────────────────────────────────────────────────────────────
// Incoming format (after Coordinator strips the base type):
//   EYE_<n>:<CMD>[:<payload>]
void EyeController::parseMessage(const String &message)
{
    int c1 = message.indexOf(':');
    if (c1 <= 0)
        return;

    String targetId = message.substring(0, c1);
    if (targetId != observerId)
        return;

    int c2 = message.indexOf(':', c1 + 1);
    String cmd = (c2 > 0) ? message.substring(c1 + 1, c2)
                          : message.substring(c1 + 1);
    String payload = (c2 > 0) ? message.substring(c2 + 1) : String("");

    if (cmd == EYE_CMD_ON)
        handleCmdOn();
    else if (cmd == EYE_CMD_OFF)
        handleCmdOff();
    else if (cmd == EYE_CMD_FILL)
        handleCmdFill(payload);
    else if (cmd == EYE_CMD_DRAW)
        handleCmdDraw(payload);
    else if (cmd == EYE_CMD_MOVE)
        handleCmdMove(payload);
}

// ─── redraw ───────────────────────────────────────────────────────────────────
// Must be called every loop() iteration.
// Smoothly interpolates gaze and repaints only when something changed.
// Does nothing in fill-only mode (_showEye == false).
void EyeController::redraw()
{
    if (!_on || !_showEye)
        return;

    // Compute pixel target from normalised gaze (−100..+100)
    int targetCx = EYE_CX + (int)((long)_gx * EYE_MAX_GAZE / 100);
    int targetCy = EYE_CY + (int)((long)_gy * EYE_MAX_GAZE / 100);

    // Exponential smoothing (~60 FPS visual)
    _fCx += ((float)targetCx - _fCx) * 0.3f;
    _fCy += ((float)targetCy - _fCy) * 0.3f;

    int icx = (int)_fCx;
    int icy = (int)_fCy;

    bool posChanged = (icx != _dCx || icy != _dCy);
    bool colourChanged = (_r != _dR || _g != _dG || _b != _dB ||
                          _bgR != _dBgR || _bgG != _dBgG || _bgB != _dBgB);

    if (posChanged || colourChanged || _dirty)
    {
        _dirty = false;
        drawEye(icx, icy, rgb565(_r, _g, _b), rgb565(_bgR, _bgG, _bgB));
        _dCx = icx;
        _dCy = icy;
        _dR = _r;
        _dG = _g;
        _dB = _b;
        _dBgR = _bgR;
        _dBgG = _bgG;
        _dBgB = _bgB;
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Command handlers
// ═══════════════════════════════════════════════════════════════════════════════

// EYE:EYE_<n>:ON
void EyeController::handleCmdOn()
{
    if (_on)
        return;
    gcCmd(0x11);
    delay(120); // Sleep-Out
    gcCmd(0x29);
    delay(20); // Display-On
    _on = true;
    _dirty = true; // repaint on next redraw()
    // Output: EYE_<n>:EYE:ok
    sendToSerial(String(EYE_PREFIX) + ":ok");
}

// EYE:EYE_<n>:OFF
void EyeController::handleCmdOff()
{
    if (!_on)
        return;
    gcCmd(0x28); // Display-Off
    gcCmd(0x10); // Sleep-In
    _on = false;
    // Output: EYE_<n>:EYE:ok
    sendToSerial(String(EYE_PREFIX) + ":ok");
}

// EYE:EYE_<n>:FILL:<r>,<g>,<b>
// Paints the entire screen in one solid colour. No eye is drawn.
void EyeController::handleCmdFill(const String &payload)
{
    int c1 = payload.indexOf(',');
    int c2 = payload.indexOf(',', c1 + 1);

    if (c1 < 0 || c2 < 0)
        return;

    uint8_t r = constrain(payload.substring(0, c1).toInt(), 0, 255);
    uint8_t g = constrain(payload.substring(c1 + 1, c2).toInt(), 0, 255);
    uint8_t b = constrain(payload.substring(c2 + 1).toInt(), 0, 255);

    _showEye = false;

    if (_on)
        fillScreen(rgb565(r, g, b));

    sendToSerial(String(EYE_PREFIX) + ":ok");
}

// EYE:EYE_<n>:DRAW:<shape>,<r>,<g>,<b>,<bg_r>,<bg_g>,<bg_b>
// Switches to eye-drawing mode.  Only "neutral" shape is implemented.
// Fills the screen with the new background first so no FILL artefacts remain.
// EYE:EYE_<n>:DRAW:<shape>,<r>,<g>,<b>,<bg_r>,<bg_g>,<bg_b>
void EyeController::handleCmdDraw(const String &payload)
{
    int c1 = payload.indexOf(',');
    int c2 = payload.indexOf(',', c1 + 1);
    int c3 = payload.indexOf(',', c2 + 1);
    int c4 = payload.indexOf(',', c3 + 1);
    int c5 = payload.indexOf(',', c4 + 1);
    int c6 = payload.indexOf(',', c5 + 1);

    if (c1 < 0 || c2 < 0 || c3 < 0 || c4 < 0 || c5 < 0)
        return;

    // shape token (currently unused)
    String shape = payload.substring(0, c1);

    _r = constrain(payload.substring(c1 + 1, c2).toInt(), 0, 255);
    _g = constrain(payload.substring(c2 + 1, c3).toInt(), 0, 255);
    _b = constrain(payload.substring(c3 + 1, c4).toInt(), 0, 255);

    _bgR = constrain(payload.substring(c4 + 1, c5).toInt(), 0, 255);
    _bgG = constrain(payload.substring(c5 + 1, c6).toInt(), 0, 255);
    _bgB = constrain(payload.substring(c6 + 1).toInt(), 0, 255);

    if (_on)
        fillScreen(rgb565(_bgR, _bgG, _bgB));

    _dCx = EYE_CX;
    _dCy = EYE_CY;
    _fCx = (float)EYE_CX;
    _fCy = (float)EYE_CY;

    _showEye = true;
    _dirty = true;

    sendToSerial(String(EYE_PREFIX) + ":ok");
}

// EYE:EYE_<n>:MOVE:<x>,<y>    x/y: −100..+100
// Updates the gaze target; redraw() handles the smooth interpolation.
// Only meaningful in DRAW mode (_showEye == true).
void EyeController::handleCmdMove(const String &payload)
{

    int comma = payload.indexOf(',');

    if (comma > 0)
    {
        int gx = payload.substring(0, comma).toInt();
        int gy = payload.substring(comma + 1).toInt();

        _gx = constrain(gx, -100, 100);
        _gy = constrain(gy, -100, 100);
    }

    sendToSerial(String(EYE_PREFIX) + ":ok");
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Draw primitives
// ═══════════════════════════════════════════════════════════════════════════════

void EyeController::fillScreen(uint16_t colour)
{
    fillRect(0, 0, EYE_SCREEN_W - 1, EYE_SCREEN_H - 1, colour);
}

void EyeController::fillRect(int x0, int y0, int x1, int y1, uint16_t colour)
{
    if (x0 < 0)
        x0 = 0;
    if (y0 < 0)
        y0 = 0;
    if (x1 >= EYE_SCREEN_W)
        x1 = EYE_SCREEN_W - 1;
    if (y1 >= EYE_SCREEN_H)
        y1 = EYE_SCREEN_H - 1;
    if (x0 > x1 || y0 > y1)
        return;

    setWindow(x0, y0, x1, y1);
    uint8_t hi = colour >> 8;
    uint8_t lo = colour & 0xFF;
    uint32_t n = (uint32_t)(x1 - x0 + 1) * (uint32_t)(y1 - y0 + 1);

    dcHigh();
    csLow();
    while (n--)
    {
        spiWrite(hi);
        spiWrite(lo);
    }
    csHigh();
}

// Union-bounding-box draw: covers both the old and new eye positions in a single
// SPI transfer, eliminating flicker.
void EyeController::drawEye(int newCx, int newCy, uint16_t eyeCol, uint16_t bgCol)
{
    int maxYDist = EYE_Y_FLAT + EYE_R + 1;
    int maxXDist = EYE_R + 1;

    int x0 = min(_dCx, newCx) - maxXDist;
    int y0 = min(_dCy, newCy) - maxYDist;
    int x1 = max(_dCx, newCx) + maxXDist;
    int y1 = max(_dCy, newCy) + maxYDist;

    if (x0 < 0)
        x0 = 0;
    if (y0 < 0)
        y0 = 0;
    if (x1 >= EYE_SCREEN_W)
        x1 = EYE_SCREEN_W - 1;
    if (y1 >= EYE_SCREEN_H)
        y1 = EYE_SCREEN_H - 1;

    uint8_t eyeHi = eyeCol >> 8, eyeLo = eyeCol & 0xFF;
    uint8_t bgHi = bgCol >> 8, bgLo = bgCol & 0xFF;

    setWindow(x0, y0, x1, y1);
    dcHigh();
    csLow();

    for (int py = y0; py <= y1; py++)
    {
        int ady = py - newCy;
        if (ady < 0)
            ady = -ady;

        if (ady >= EYE_SPAN_SIZE)
        {
            // Fully outside capsule — paint background for the whole row
            for (int px = x0; px <= x1; px++)
            {
                spiWrite(bgHi);
                spiWrite(bgLo);
            }
        }
        else
        {
            uint8_t xs = _eyeSpan[ady];
            int cl = newCx - (int)xs;
            if (cl < x0)
                cl = x0;
            int cr = newCx + (int)xs;
            if (cr > x1)
                cr = x1;

            for (int px = x0; px < cl; px++)
            {
                spiWrite(bgHi);
                spiWrite(bgLo);
            }
            for (int px = cl; px <= cr; px++)
            {
                spiWrite(eyeHi);
                spiWrite(eyeLo);
            }
            for (int px = cr + 1; px <= x1; px++)
            {
                spiWrite(bgHi);
                spiWrite(bgLo);
            }
        }
    }
    csHigh();
}

// ═══════════════════════════════════════════════════════════════════════════════
//  GC9A01 initialisation
// ═══════════════════════════════════════════════════════════════════════════════

void EyeController::initGC9A01()
{
    digitalWrite(_pinRst, HIGH);
    delay(50);
    digitalWrite(_pinRst, LOW);
    delay(100);
    digitalWrite(_pinRst, HIGH);
    delay(50);

    gcCmd(0xEF);
    gcCmd(0xEB);
    gcDat1(0x14);
    gcCmd(0xFE);
    gcCmd(0xEF);
    gcCmd(0xEB);
    gcDat1(0x14);
    gcCmd(0x84);
    gcDat1(0x40);
    gcCmd(0x85);
    gcDat1(0xFF);
    gcCmd(0x86);
    gcDat1(0xFF);
    gcCmd(0x87);
    gcDat1(0xFF);
    gcCmd(0x88);
    gcDat1(0x0A);
    gcCmd(0x89);
    gcDat1(0x21);
    gcCmd(0x8A);
    gcDat1(0x00);
    gcCmd(0x8B);
    gcDat1(0x80);
    gcCmd(0x8C);
    gcDat1(0x01);
    gcCmd(0x8D);
    gcDat1(0x01);
    gcCmd(0x8E);
    gcDat1(0xFF);
    gcCmd(0x8F);
    gcDat1(0xFF);
    {
        uint8_t d[] = {0x00, 0x20};
        gcCmd(0xB6);
        gcDatN(d, 2);
    }
    gcCmd(0x36);
    gcDat1(0x08);
    gcCmd(0x3A);
    gcDat1(0x05);
    {
        uint8_t d[] = {0x08, 0x08, 0x08, 0x08};
        gcCmd(0x90);
        gcDatN(d, 4);
    }
    gcCmd(0xBD);
    gcDat1(0x06);
    gcCmd(0xBC);
    gcDat1(0x00);
    {
        uint8_t d[] = {0x60, 0x01, 0x04};
        gcCmd(0xFF);
        gcDatN(d, 3);
    }
    gcCmd(0xC3);
    gcDat1(0x13);
    gcCmd(0xC4);
    gcDat1(0x13);
    gcCmd(0xC9);
    gcDat1(0x22);
    gcCmd(0xBE);
    gcDat1(0x11);
    {
        uint8_t d[] = {0x10, 0x0E};
        gcCmd(0xE1);
        gcDatN(d, 2);
    }
    {
        uint8_t d[] = {0x21, 0x0C, 0x02};
        gcCmd(0xDF);
        gcDatN(d, 3);
    }
    {
        uint8_t d[] = {0x45, 0x09, 0x08, 0x08, 0x26, 0x2A};
        gcCmd(0xF0);
        gcDatN(d, 6);
    }
    {
        uint8_t d[] = {0x43, 0x70, 0x72, 0x36, 0x37, 0x6F};
        gcCmd(0xF1);
        gcDatN(d, 6);
    }
    {
        uint8_t d[] = {0x45, 0x09, 0x08, 0x08, 0x26, 0x2A};
        gcCmd(0xF2);
        gcDatN(d, 6);
    }
    {
        uint8_t d[] = {0x43, 0x70, 0x72, 0x36, 0x37, 0x6F};
        gcCmd(0xF3);
        gcDatN(d, 6);
    }
    {
        uint8_t d[] = {0x1B, 0x0B};
        gcCmd(0xED);
        gcDatN(d, 2);
    }
    gcCmd(0xAE);
    gcDat1(0x77);
    gcCmd(0xCD);
    gcDat1(0x63);
    {
        uint8_t d[] = {0x07, 0x07, 0x04, 0x0E, 0x0F, 0x09, 0x07, 0x08, 0x03};
        gcCmd(0x70);
        gcDatN(d, 9);
    }
    gcCmd(0xE8);
    gcDat1(0x34);
    {
        uint8_t d[] = {0x18, 0x0D, 0x71, 0xED, 0x70, 0x70,
                       0x18, 0x0F, 0x71, 0xEF, 0x70, 0x70};
        gcCmd(0x62);
        gcDatN(d, 12);
    }
    {
        uint8_t d[] = {0x18, 0x11, 0x71, 0xF1, 0x70, 0x70,
                       0x18, 0x13, 0x71, 0xF3, 0x70, 0x70};
        gcCmd(0x63);
        gcDatN(d, 12);
    }
    {
        uint8_t d[] = {0x28, 0x29, 0xF1, 0x01, 0xF1, 0x00, 0x07};
        gcCmd(0x64);
        gcDatN(d, 7);
    }
    {
        uint8_t d[] = {0x3C, 0x00, 0xCD, 0x67, 0x45, 0x45,
                       0x10, 0x00, 0x00, 0x00};
        gcCmd(0x66);
        gcDatN(d, 10);
    }
    {
        uint8_t d[] = {0x00, 0x3C, 0x00, 0x00, 0x00, 0x01,
                       0x54, 0x10, 0x32, 0x98};
        gcCmd(0x67);
        gcDatN(d, 10);
    }
    {
        uint8_t d[] = {0x10, 0x85, 0x80, 0x00, 0x00, 0x4E, 0x00};
        gcCmd(0x74);
        gcDatN(d, 7);
    }
    {
        uint8_t d[] = {0x3E, 0x07};
        gcCmd(0x98);
        gcDatN(d, 2);
    }
    gcCmd(0x35);
    gcCmd(0x21);
    gcCmd(0x11);
    delay(120);
    gcCmd(0x29);
    delay(20);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Low-level SPI helpers
// ═══════════════════════════════════════════════════════════════════════════════

void EyeController::spiWrite(uint8_t b)
{
#if defined(SPDR) && defined(SPIF)
    SPDR = b;
    while (!(SPSR & _BV(SPIF)))
        ;
#else
    SPI.transfer(b);
#endif
}

void EyeController::gcCmd(uint8_t cmd)
{
    dcLow();
    csLow();
    spiWrite(cmd);
    csHigh();
}

void EyeController::gcDat1(uint8_t d)
{
    dcHigh();
    csLow();
    spiWrite(d);
    csHigh();
}

void EyeController::gcDatN(const uint8_t *d, uint8_t n)
{
    dcHigh();
    csLow();
    while (n--)
        spiWrite(*d++);
    csHigh();
}

void EyeController::setWindow(int x0, int y0, int x1, int y1)
{
    gcCmd(0x2A);
    dcHigh();
    csLow();
    spiWrite(0);
    spiWrite((uint8_t)x0);
    spiWrite(0);
    spiWrite((uint8_t)x1);
    csHigh();

    gcCmd(0x2B);
    dcHigh();
    csLow();
    spiWrite(0);
    spiWrite((uint8_t)y0);
    spiWrite(0);
    spiWrite((uint8_t)y1);
    csHigh();

    gcCmd(0x2C);
}

// ═══════════════════════════════════════════════════════════════════════════════
//  Static helpers
// ═══════════════════════════════════════════════════════════════════════════════

uint16_t EyeController::rgb565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((uint16_t)(r >> 3) << 11) | ((uint16_t)(g >> 2) << 5) | (uint16_t)(b >> 3);
}