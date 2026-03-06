#include "EyeController.h"

EyeController::EyeController(const String &id, int pinCs, int pinDc, int pinRst, int pinMosi, int pinSclk, bool mirrored)
    : GeneralController(id),
      _pinCs(pinCs), _pinDc(pinDc), _pinRst(pinRst),
      _mirrored(mirrored),
      _s_r(60), _s_g(150), _s_b(240),
      _s_gx(0), _s_gy(0),
      _new_cmd(false),
      _d_cx(EYE_CX), _d_cy(EYE_CY),
      _d_r(0), _d_g(0), _d_b(0)
{
    // Precalcular semiancho por fila para iris y pupila
    for (uint8_t dy = 0; dy <= BALL_R; dy++) {
        long dy2 = (long)dy * dy;
        _circ_span[dy] = (dy2 > BALL_R2) ? 0 : (uint8_t)sqrt((float)(BALL_R2 - dy2));
    }
    for (uint8_t dy = 0; dy <= PUPIL_R; dy++) {
        long dy2 = (long)dy * dy;
        _pupl_span[dy] = (dy2 > PUPIL_R2) ? 0 : (uint8_t)sqrt((float)(PUPIL_R2 - dy2));
    }
}

void EyeController::begin()
{
    pinMode(_pinRst, OUTPUT);
    pinMode(_pinCs,  OUTPUT);
    pinMode(_pinDc,  OUTPUT);
    digitalWrite(_pinCs, HIGH);
    digitalWrite(_pinDc, HIGH);

    SPI.begin();
    // SPI transaction should be handled per-transfer if multiple devices share the bus,
    // or kept global if this is the only user. For simplicity, we assume we own it or start transaction.
    SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));

    initGC9A01();
    fillRect(0, 0, 239, 239, 0x0000);
}

void EyeController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    const uint16_t colors[] = {0xF800, 0x07E0, 0x001F};
    for (uint16_t c : colors)
    {
        fillRect(0, 0, 239, 239, c);
        delay(150);
    }
    
    fillRect(0, 0, 239, 239, 0x0000);
    _new_cmd = true; // Trigger redraw
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

    // Format: gx,gy,r,g,b
    int i0 = payload.indexOf(',');
    int i1 = (i0 >= 0) ? payload.indexOf(',', i0 + 1) : -1;
    int i2 = (i1 >= 0) ? payload.indexOf(',', i1 + 1) : -1;
    int i3 = (i2 >= 0) ? payload.indexOf(',', i2 + 1) : -1;

    if (i3 < 0) return; // Need at least 4 commas for 5 values

    int raw_gx = payload.substring(0, i0).toInt();
    int raw_gy = payload.substring(i0 + 1, i1).toInt();
    int raw_r  = payload.substring(i1 + 1, i2).toInt();
    int raw_g  = payload.substring(i2 + 1, i3).toInt();
    int raw_b  = payload.substring(i3 + 1).toInt();

    _s_gx = constrain(raw_gx, -100, 100);
    _s_gy = constrain(raw_gy, -100, 100);
    _s_r  = (uint8_t)constrain(raw_r, 0, 255);
    _s_g  = (uint8_t)constrain(raw_g, 0, 255);
    _s_b  = (uint8_t)constrain(raw_b, 0, 255);
    
    _new_cmd = true;
    sendToSerial(F("EYE:ok"));
}

void EyeController::redraw()
{
    if (!_new_cmd) return;
    _new_cmd = false;

    int gx = _mirrored ? -_s_gx : _s_gx;
    int gy = _s_gy;

    int new_cx = EYE_CX + (int)((long)gx * MAX_GAZE / 100);
    int new_cy = EYE_CY + (int)((long)gy * MAX_GAZE / 100);

    uint16_t col = rgb565(_s_r, _s_g, _s_b);
    drawBall(new_cx, new_cy, col);
    drawHighlight(new_cx, new_cy, col >> 8, col & 0xFF);

    _d_cx = new_cx; _d_cy = new_cy;
    _d_r = _s_r; _d_g = _s_g; _d_b = _s_b;
}

// ─── SPI bajo nivel ──────────────────────────────────────────────────────────
void EyeController::gc_cmd(uint8_t cmd) {
    digitalWrite(_pinDc, LOW);  digitalWrite(_pinCs, LOW);
    SPI.transfer(cmd);
    digitalWrite(_pinCs, HIGH);
}
void EyeController::gc_dat1(uint8_t d) {
    digitalWrite(_pinDc, HIGH); digitalWrite(_pinCs, LOW);
    SPI.transfer(d);
    digitalWrite(_pinCs, HIGH);
}
void EyeController::gc_datn(const uint8_t* d, uint8_t n) {
    digitalWrite(_pinDc, HIGH); digitalWrite(_pinCs, LOW);
    while (n--) SPI.transfer(*d++);
    digitalWrite(_pinCs, HIGH);
}
void EyeController::setWindow(int x0, int y0, int x1, int y1) {
    gc_cmd(0x2A);
    uint8_t xa[] = { 0, (uint8_t)x0, 0, (uint8_t)x1 };
    gc_datn(xa, 4);
    gc_cmd(0x2B);
    uint8_t ya[] = { 0, (uint8_t)y0, 0, (uint8_t)y1 };
    gc_datn(ya, 4);
    gc_cmd(0x2C);
}

void EyeController::fillRect(int x0, int y0, int x1, int y1, uint16_t col) {
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;
    if (x0 > x1 || y0 > y1) return;
    setWindow(x0, y0, x1, y1);
    uint8_t hi = col >> 8, lo = col & 0xFF;
    uint32_t n = (uint32_t)(x1 - x0 + 1) * (y1 - y0 + 1);
    digitalWrite(_pinDc, HIGH); digitalWrite(_pinCs, LOW);
    while (n--) {
        SPDR = hi; while (!(SPSR & _BV(SPIF)));
        SPDR = lo; while (!(SPSR & _BV(SPIF)));
    }
    digitalWrite(_pinCs, HIGH);
}

void EyeController::drawBall(int new_cx, int new_cy, uint16_t col) {
    int x0 = min(_d_cx, new_cx) - BALL_R - 1;
    int y0 = min(_d_cy, new_cy) - BALL_R - 1;
    int x1 = max(_d_cx, new_cx) + BALL_R + 1;
    int y1 = max(_d_cy, new_cy) + BALL_R + 1;
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;

    uint8_t hi = col >> 8, lo = col & 0xFF;
    setWindow(x0, y0, x1, y1);
    digitalWrite(_pinDc, HIGH); digitalWrite(_pinCs, LOW);

    for (int py = y0; py <= y1; py++) {
        int ady = py - new_cy;
        if (ady < 0) ady = -ady;

        if (ady > BALL_R) {
            for (int px = x0; px <= x1; px++) {
                SPDR = 0; while (!(SPSR & _BV(SPIF)));
                SPDR = 0; while (!(SPSR & _BV(SPIF)));
            }
        } else {
            uint8_t xs = _circ_span[ady];
            int cl = new_cx - xs; if (cl < x0) cl = x0;
            int cr = new_cx + xs; if (cr > x1) cr = x1;

            if (ady <= PUPIL_R) {
                uint8_t ps = _pupl_span[ady];
                int pl = new_cx - ps; if (pl < x0) pl = x0;
                int pr = new_cx + ps; if (pr > x1) pr = x1;

                for (int px = x0;    px <  cl; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
                for (int px = cl;    px <  pl; px++) { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
                for (int px = pl;    px <= pr; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
                for (int px = pr+1;  px <= cr; px++) { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
                for (int px = cr+1;  px <= x1; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
            } else {
                for (int px = x0;   px <  cl; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
                for (int px = cl;   px <= cr; px++) { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
                for (int px = cr+1; px <= x1; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
            }
        }
    }
    digitalWrite(_pinCs, HIGH);
}

void EyeController::drawHighlight(int cx, int cy, uint8_t hi, uint8_t lo) {
    int hx = cx + HIGHL_OX;
    int hy = cy - HIGHL_OY;
    int x0 = hx - HIGHL_R, x1 = hx + HIGHL_R;
    int y0 = hy - HIGHL_R, y1 = hy + HIGHL_R;
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;

    static const uint8_t HIGHL_SPAN[] = {3, 3, 2, 1};

    setWindow(x0, y0, x1, y1);
    digitalWrite(_pinDc, HIGH); digitalWrite(_pinCs, LOW);
    for (int py = y0; py <= y1; py++) {
        int ady = py - hy; if (ady < 0) ady = -ady;
        uint8_t xs = (ady <= HIGHL_R) ? HIGHL_SPAN[ady] : 0;
        int hl = hx - xs, hr = hx + xs;
        for (int px = x0; px <= x1; px++) {
            if (px >= hl && px <= hr) {
                SPDR = 0xFF; while (!(SPSR & _BV(SPIF)));
                SPDR = 0xFF; while (!(SPSR & _BV(SPIF)));
            } else {
                SPDR = hi; while (!(SPSR & _BV(SPIF)));
                SPDR = lo; while (!(SPSR & _BV(SPIF)));
            }
        }
    }
    digitalWrite(_pinCs, HIGH);
}

void EyeController::initGC9A01() {
    digitalWrite(_pinRst, HIGH); delay(50);
    digitalWrite(_pinRst, LOW);  delay(100);
    digitalWrite(_pinRst, HIGH); delay(50);

    gc_cmd(0xEF);
    gc_cmd(0xEB); gc_dat1(0x14);
    gc_cmd(0xFE);
    gc_cmd(0xEF);
    gc_cmd(0xEB); gc_dat1(0x14);
    gc_cmd(0x84); gc_dat1(0x40);
    gc_cmd(0x85); gc_dat1(0xFF);
    gc_cmd(0x86); gc_dat1(0xFF);
    gc_cmd(0x87); gc_dat1(0xFF);
    gc_cmd(0x88); gc_dat1(0x0A);
    gc_cmd(0x89); gc_dat1(0x21);
    gc_cmd(0x8A); gc_dat1(0x00);
    gc_cmd(0x8B); gc_dat1(0x80);
    gc_cmd(0x8C); gc_dat1(0x01);
    gc_cmd(0x8D); gc_dat1(0x01);
    gc_cmd(0x8E); gc_dat1(0xFF);
    gc_cmd(0x8F); gc_dat1(0xFF);
    { uint8_t d[]={0x00,0x20};                         gc_cmd(0xB6); gc_datn(d,2); }
    gc_cmd(0x36); gc_dat1(0x08);
    gc_cmd(0x3A); gc_dat1(0x05);
    { uint8_t d[]={0x08,0x08,0x08,0x08};               gc_cmd(0x90); gc_datn(d,4); }
    gc_cmd(0xBD); gc_dat1(0x06);
    gc_cmd(0xBC); gc_dat1(0x00);
    { uint8_t d[]={0x60,0x01,0x04};                    gc_cmd(0xFF); gc_datn(d,3); }
    gc_cmd(0xC3); gc_dat1(0x13);
    gc_cmd(0xC4); gc_dat1(0x13);
    gc_cmd(0xC9); gc_dat1(0x22);
    gc_cmd(0xBE); gc_dat1(0x11);
    { uint8_t d[]={0x10,0x0E};                         gc_cmd(0xE1); gc_datn(d,2); }
    { uint8_t d[]={0x21,0x0C,0x02};                    gc_cmd(0xDF); gc_datn(d,3); }
    { uint8_t d[]={0x45,0x09,0x08,0x08,0x26,0x2A};     gc_cmd(0xF0); gc_datn(d,6); }
    { uint8_t d[]={0x43,0x70,0x72,0x36,0x37,0x6F};     gc_cmd(0xF1); gc_datn(d,6); }
    { uint8_t d[]={0x45,0x09,0x08,0x08,0x26,0x2A};     gc_cmd(0xF2); gc_datn(d,6); }
    { uint8_t d[]={0x43,0x70,0x72,0x36,0x37,0x6F};     gc_cmd(0xF3); gc_datn(d,6); }
    { uint8_t d[]={0x1B,0x0B};                         gc_cmd(0xED); gc_datn(d,2); }
    gc_cmd(0xAE); gc_dat1(0x77);
    gc_cmd(0xCD); gc_dat1(0x63);
    { uint8_t d[]={0x07,0x07,0x04,0x0E,0x0F,0x09,0x07,0x08,0x03};
                                                        gc_cmd(0x70); gc_datn(d,9); }
    gc_cmd(0xE8); gc_dat1(0x34);
    { uint8_t d[]={0x18,0x0D,0x71,0xED,0x70,0x70,0x18,0x0F,0x71,0xEF,0x70,0x70};
                                                        gc_cmd(0x62); gc_datn(d,12); }
    { uint8_t d[]={0x18,0x11,0x71,0xF1,0x70,0x70,0x18,0x13,0x71,0xF3,0x70,0x70};
                                                        gc_cmd(0x63); gc_datn(d,12); }
    { uint8_t d[]={0x28,0x29,0xF1,0x01,0xF1,0x00,0x07}; gc_cmd(0x64); gc_datn(d,7); }
    { uint8_t d[]={0x3C,0x00,0xCD,0x67,0x45,0x45,0x10,0x00,0x00,0x00};
                                                        gc_cmd(0x66); gc_datn(d,10); }
    { uint8_t d[]={0x00,0x3C,0x00,0x00,0x00,0x01,0x54,0x10,0x32,0x98};
                                                        gc_cmd(0x67); gc_datn(d,10); }
    { uint8_t d[]={0x10,0x85,0x80,0x00,0x00,0x4E,0x00}; gc_cmd(0x74); gc_datn(d,7); }
    { uint8_t d[]={0x3E,0x07};                         gc_cmd(0x98); gc_datn(d,2); }
    gc_cmd(0x35);
    gc_cmd(0x21);
    gc_cmd(0x11); delay(120);
    gc_cmd(0x29); delay(20);
}
