#include "EyeController.h"

// Semianchos para los brillos "cute"
static const uint8_t HIGHL_SPAN_FAST[] = {5, 5, 4, 4, 3, 2};
static const uint8_t HIGHL2_SPAN_FAST[] = {3, 3, 2, 1};

EyeController::EyeController(const String &id, int pinCs, int pinDc, int pinRst, int pinMosi, int pinSclk, bool mirrored)
    : GeneralController(id, EYE_BASE_ID),
      _pinCs(pinCs), _pinDc(pinDc), _pinRst(pinRst),
      _mirrored(mirrored),
      _s_r(60), _s_g(150), _s_b(240),
      _s_gx(0), _s_gy(0),
      _s_shape(PUPIL_CIRCLE),
      _new_cmd(false),
      _d_cx(EYE_CX), _d_cy(EYE_CY),
      _d_r(0), _d_g(0), _d_b(0),
      _d_shape(PUPIL_CIRCLE),
      _f_cx(EYE_CX), _f_cy(EYE_CY)
{
    // Calcular máscaras para Port L (Mega 2560)
    // Pin 49=PL0, 48=PL1, 47=PL2, 46=PL3
    _cs_mask  = _BV(49 - pinCs);   // Error en lógica anterior, re-calculando:
    // Pin 49 -> Bit 0: mask = _BV(49-49) = _BV(0)
    // Pin 48 -> Bit 1: mask = _BV(49-48) = _BV(1)
    // Pin 47 -> Bit 2: mask = _BV(49-47) = _BV(2)
    // Pin 46 -> Bit 3: mask = _BV(49-46) = _BV(3)
    _cs_mask  = _BV(49 - pinCs);
    _dc_mask  = _BV(49 - pinDc);
    _rst_mask = _BV(49 - pinRst);

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
    CS_HIGH();
    DC_HIGH();

    SPI.begin();
    SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));

    initGC9A01();
    fillRect(0, 0, 239, 239, 0x0000);
}

void EyeController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    // Exercise the message pipeline by sending high-level eye commands as if
    // they were coming from the Coordinator.

    // Cycle some colours
    Update(observerId + ":" + String(EYE_CMD_COLOR) + ":255,0,0");
    delay(200);
    Update(observerId + ":" + String(EYE_CMD_COLOR) + ":0,255,0");
    delay(200);
    Update(observerId + ":" + String(EYE_CMD_COLOR) + ":0,0,255");
    delay(200);

    // Cycle through shapes
    Update(observerId + ":" + String(EYE_CMD_SHAPE) + ":circle");
    delay(250);
    Update(observerId + ":" + String(EYE_CMD_SHAPE) + ":star");
    delay(250);
    Update(observerId + ":" + String(EYE_CMD_SHAPE) + ":smiley");
    delay(250);
    Update(observerId + ":" + String(EYE_CMD_SHAPE) + ":x");
    delay(250);

    // Simple gaze move and reset back to centre with neutral colour
    Update(observerId + ":30,-10,255,200,0");
    delay(250);
    Update(observerId + ":0,0,60,150,240");

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
    String command  = message.substring(colonIndex + 1);

    if (targetId != observerId) return;

    if (command.startsWith(EYE_CMD_COLOR)) {
        handleColorCommand(command);
    } else if (command.startsWith(EYE_CMD_SHAPE)) {
        handleShapeCommand(command);
    } else {
        handleGazeCommand(command);
    }
}

void EyeController::handleColorCommand(const String &command)
{
    // Format: COLOR:r,g,b
    int dataColon = command.indexOf(':');
    if (dataColon <= 0) return;

    String colors = command.substring(dataColon + 1);
    int c1 = colors.indexOf(',');
    int c2 = colors.lastIndexOf(',');
    if (c1 <= 0 || c2 <= c1) return;

    _s_r = (uint8_t)constrain(colors.substring(0, c1).toInt(), 0, 255);
    _s_g = (uint8_t)constrain(colors.substring(c1 + 1, c2).toInt(), 0, 255);
    _s_b = (uint8_t)constrain(colors.substring(c2 + 1).toInt(), 0, 255);

    _new_cmd = true;
    sendToSerial(String(EYE_PREFIX) + ":ok");
}

void EyeController::handleShapeCommand(const String &command)
{
    // Format: SHAPE:type
    int dataColon = command.indexOf(':');
    if (dataColon <= 0) return;

    String shapeType = command.substring(dataColon + 1);
    shapeType.toLowerCase();

    if (shapeType == "circle") _s_shape = PUPIL_CIRCLE;
    else if (shapeType == "star")   _s_shape = PUPIL_STAR;
    else if (shapeType == "smiley") _s_shape = PUPIL_SMILEY;
    else if (shapeType == "x")      _s_shape = PUPIL_X;
    else return;

    _new_cmd = true;
    sendToSerial(String(EYE_PREFIX) + ":ok");
}

void EyeController::handleGazeCommand(const String &command)
{
    // Format: gx,gy,r,g,b
    int i0 = command.indexOf(',');
    int i1 = (i0 >= 0) ? command.indexOf(',', i0 + 1) : -1;
    int i2 = (i1 >= 0) ? command.indexOf(',', i1 + 1) : -1;
    int i3 = (i2 >= 0) ? command.indexOf(',', i2 + 1) : -1;

    if (i3 < 0) return;

    int raw_gx = command.substring(0, i0).toInt();
    int raw_gy = command.substring(i0 + 1, i1).toInt();
    int raw_r  = command.substring(i1 + 1, i2).toInt();
    int raw_g  = command.substring(i2 + 1, i3).toInt();
    int raw_b  = command.substring(i3 + 1).toInt();

    _s_gx = constrain(raw_gx, -100, 100);
    _s_gy = constrain(raw_gy, -100, 100);
    _s_r  = (uint8_t)constrain(raw_r, 0, 255);
    _s_g  = (uint8_t)constrain(raw_g, 0, 255);
    _s_b  = (uint8_t)constrain(raw_b, 0, 255);

    _new_cmd = true;
    sendToSerial(String(EYE_PREFIX) + ":ok");
}

void EyeController::redraw()
{
    int gx = _mirrored ? -_s_gx : _s_gx;
    int gy = _s_gy;

    int target_cx = EYE_CX + (int)((long)gx * MAX_GAZE / 100);
    int target_cy = EYE_CY + (int)((long)gy * MAX_GAZE / 100);

    // Suavizado (Interpolación 60 FPS)
    _f_cx += ((float)target_cx - _f_cx) * 0.3f;
    _f_cy += ((float)target_cy - _f_cy) * 0.3f;

    int icx = (int)_f_cx;
    int icy = (int)_f_cy;

    if (icx != _d_cx || icy != _d_cy || _new_cmd) {
        _new_cmd = false;
        uint16_t col = rgb565(_s_r, _s_g, _s_b);
        drawBall(icx, icy, col, _s_shape);
        drawHighlight(icx, icy, col);

        _d_cx = icx; _d_cy = icy;
        _d_r = _s_r; _d_g = _s_g; _d_b = _s_b;
        _d_shape = _s_shape;
    }
}

// ─── SPI bajo nivel (Optimized) ──────────────────────────────────────────────
void EyeController::gc_cmd(uint8_t cmd) {
    DC_LOW(); CS_LOW();
    SPDR = cmd; while (!(SPSR & _BV(SPIF)));
    CS_HIGH();
}
void EyeController::gc_dat1(uint8_t d) {
    DC_HIGH(); CS_LOW();
    SPDR = d; while (!(SPSR & _BV(SPIF)));
    CS_HIGH();
}
void EyeController::gc_datn(const uint8_t* d, uint8_t n) {
    DC_HIGH(); CS_LOW();
    while (n--) {
        SPDR = *d++; while (!(SPSR & _BV(SPIF)));
    }
    CS_HIGH();
}
void EyeController::setWindow(int x0, int y0, int x1, int y1) {
    gc_cmd(0x2A);
    DC_HIGH(); CS_LOW();
    SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = (uint8_t)x0; while (!(SPSR & _BV(SPIF)));
    SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = (uint8_t)x1; while (!(SPSR & _BV(SPIF)));
    CS_HIGH();

    gc_cmd(0x2B);
    DC_HIGH(); CS_LOW();
    SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = (uint8_t)y0; while (!(SPSR & _BV(SPIF)));
    SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = (uint8_t)y1; while (!(SPSR & _BV(SPIF)));
    CS_HIGH();
    
    gc_cmd(0x2C);
}

void EyeController::fillRect(int x0, int y0, int x1, int y1, uint16_t col) {
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;
    if (x0 > x1 || y0 > y1) return;
    setWindow(x0, y0, x1, y1);
    uint8_t hi = col >> 8, lo = col & 0xFF;
    uint32_t n = (uint32_t)(x1 - x0 + 1) * (y1 - y0 + 1);
    DC_HIGH(); CS_LOW();
    while (n--) {
        SPDR = hi; while (!(SPSR & _BV(SPIF)));
        SPDR = lo; while (!(SPSR & _BV(SPIF)));
    }
    CS_HIGH();
}

void EyeController::drawBall(int icx, int icy, uint16_t col, PupilShape shape) {
    int x0 = min(_d_cx, icx) - BALL_R - 1;
    int y0 = min(_d_cy, icy) - BALL_R - 1;
    int x1 = max(_d_cx, icx) + BALL_R + 1;
    int y1 = max(_d_cy, icy) + BALL_R + 1;
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;

    uint8_t hi = col >> 8, lo = col & 0xFF;
    setWindow(x0, y0, x1, y1);
    DC_HIGH(); CS_LOW();

    for (int py = y0; py <= y1; py++) {
        int ady = py - icy;
        if (ady < 0) ady = -ady;

        if (ady > BALL_R) {
            for (int px = x1 - x0 + 1; px > 0; px--) {
                SPDR = 0; while (!(SPSR & _BV(SPIF)));
                SPDR = 0; while (!(SPSR & _BV(SPIF)));
            }
        } else {
            uint8_t xs = _circ_span[ady];
            int cl = icx - xs; if (cl < x0) cl = x0;
            int cr = icx + xs; if (cr > x1) cr = x1;

            if (ady <= PUPIL_R) {
                // Determine if we are inside the pupil based on shape
                int adx_limit = _pupl_span[ady];
                
                for (int px = x0; px <= x1; px++) {
                    int adx = px - icx;
                    if (adx < 0) adx = -adx;

                    bool inIris = (px >= cl && px <= cr);
                    bool inPupil = false;

                    if (inIris && adx <= adx_limit) {
                        if (shape == PUPIL_CIRCLE) {
                            inPupil = true;
                        } else if (shape == PUPIL_X) {
                            // X shape: diagonals within the pupil circle
                            // px-icx == py-icy or px-icx == -(py-icy)
                            int dx = px - icx;
                            int dy = py - icy;
                            if (abs(dx) == abs(dy) || abs(dx) == abs(dy) + 1 || abs(dx) == abs(dy) - 1) inPupil = true;
                            // Add some thickness
                        } else if (shape == PUPIL_STAR) {
                            // Star shape: simple cross + diagonal cross
                            int dx = px - icx;
                            int dy = py - icy;
                            if (abs(dx) < 3 || abs(dy) < 3 || abs(dx) == abs(dy)) inPupil = true;
                        } else if (shape == PUPIL_SMILEY) {
                            // Smiley face: two eyes and a mouth curve
                            int dx = px - icx;
                            int dy = py - icy;
                            // Eyes
                            if (dy < -8 && dy > -15 && abs(abs(dx) - 10) < 3) inPupil = true;
                            // Mouth curve: y = 0.1 * x^2 + 5 roughly
                            if (dy > 5 && dy < 15 && dy > (dx*dx/25 + 5) && dy < (dx*dx/25 + 10)) inPupil = true;
                        }
                    }

                    if (inPupil) {
                        SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = 0; while (!(SPSR & _BV(SPIF)));
                    } else if (inIris) {
                        SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF)));
                    } else {
                        SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = 0; while (!(SPSR & _BV(SPIF)));
                    }
                }
            } else {
                for (int px = x0;   px <  cl; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
                for (int px = cl;   px <= cr; px++) { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
                for (int px = cr+1; px <= x1; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
            }
        }
    }
    CS_HIGH();
}

void EyeController::drawHighlight(int cx, int cy, uint16_t irisCol) {
    uint8_t hi = irisCol >> 8, lo = irisCol & 0xFF;
    
    // Highlight 1 (Grande)
    int hx = cx + HIGHL_OX, hy = cy - HIGHL_OY;
    int x0 = hx - HIGHL_R, x1 = hx + HIGHL_R;
    int y0 = hy - HIGHL_R, y1 = hy + HIGHL_R;
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;
    setWindow(x0, y0, x1, y1);
    DC_HIGH(); CS_LOW();
    for (int py = y0; py <= y1; py++) {
        int ady = py - hy; if (ady < 0) ady = -ady;
        uint8_t xs = (ady < 6) ? HIGHL_SPAN_FAST[ady] : 0;
        int hl = hx - xs, hr = hx + xs;
        for (int px = x0; px <= x1; px++) {
            if (px >= hl && px <= hr) { SPDR = 0xFF; while (!(SPSR & _BV(SPIF))); SPDR = 0xFF; while (!(SPSR & _BV(SPIF))); }
            else { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
        }
    }
    CS_HIGH();

    // Highlight 2 (Pequeño / Brillo secundario "cute")
    hx = cx + HIGHL2_OX; hy = cy - HIGHL2_OY;
    x0 = hx - HIGHL2_R; x1 = hx + HIGHL2_R;
    y0 = hy - HIGHL2_R; y1 = hy + HIGHL2_R;
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;
    setWindow(x0, y0, x1, y1);
    DC_HIGH(); CS_LOW();
    for (int py = y0; py <= y1; py++) {
        int ady = py - hy; if (ady < 0) ady = -ady;
        uint8_t xs = (ady < 4) ? HIGHL2_SPAN_FAST[ady] : 0;
        int hl = hx - xs, hr = hx + xs;
        for (int px = x0; px <= x1; px++) {
            if (px >= hl && px <= hr) { SPDR = 0xFF; while (!(SPSR & _BV(SPIF))); SPDR = 0xFF; while (!(SPSR & _BV(SPIF))); }
            else { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
        }
    }
    CS_HIGH();
}

void EyeController::initGC9A01() {
    uint8_t rst_low = PORTL & ~_rst_mask;
    uint8_t rst_high = PORTL | _rst_mask;
    
    PORTL = rst_high; delay(50);
    PORTL = rst_low;  delay(100);
    PORTL = rst_high; delay(50);

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
