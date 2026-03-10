#ifndef EYE_CONTROLLER_H
#define EYE_CONTROLLER_H

#include "GeneralController.h"
#include <SPI.h>

// ---------------------------------------------------------------------------
// Display geometry (GC9A01 – 240×240 round display)
// ---------------------------------------------------------------------------
#define EYE_CX 120 // Screen centre X
#define EYE_CY 120 // Screen centre Y
#define SCREEN_W 240
#define SCREEN_H 240
#define MAX_GAZE 50 // Max gaze pixel offset from screen centre

// ---------------------------------------------------------------------------
// Eye-shape geometry
//
//  Neutral  – tall vertical pill (ellipse, wide=80, tall=100)
//  Happy    – bottom half of a wide, flat ellipse  (FLUJO 3)
//  Sad      – top    half of a wide, flat ellipse  (FLUJO 2)
//
//  Transition is a continuous blend of the two ellipse parameter sets.
// ---------------------------------------------------------------------------
#define EYE_AX_NEUTRAL 40 // Neutral pill: horizontal semi-axis
#define EYE_AY_NEUTRAL 50 // Neutral pill: vertical   semi-axis
#define EYE_AX_EXPR 90    // Happy / Sad arc: horizontal semi-axis
#define EYE_AY_EXPR 25    // Happy / Sad arc: vertical   semi-axis

// ---------------------------------------------------------------------------
// Idle blink timing  (FLUJO 1 – squint animation)
// ---------------------------------------------------------------------------
#define BLINK_INTERVAL_MS 3500 // Time between blinks (ms)
#define BLINK_CLOSE_MS 120     // Time to fully close  (ms)
#define BLINK_OPEN_MS 100      // Time to fully open   (ms)

// ---------------------------------------------------------------------------

class EyeController : public GeneralController
{
public:
    EyeController(const String &id,
                  int pinCs, int pinDc, int pinRst,
                  int pinMosi, int pinSclk,
                  bool mirrored = false);

    void sanityTest() override;
    void Update(const String &message) override;
    void redraw(); // Call every loop() iteration for smooth animation
    void begin();

protected:
    void parseMessage(const String &message) override;

    enum EyeShape
    {
        SHAPE_NEUTRAL,
        SHAPE_HAPPY,
        SHAPE_SAD
    };
    enum EyeMode
    {
        MODE_OFF,
        MODE_FILL,
        MODE_DRAW
    };

private:
    // ── Hardware ──────────────────────────────────────────────────────────────
    int _pinCs, _pinDc, _pinRst;
    uint8_t _cs_mask, _dc_mask, _rst_mask;
    bool _mirrored;

    // ── Target state  (written by protocol command handlers) ─────────────────
    EyeMode _s_mode;
    EyeShape _s_shape;
    uint8_t _s_r, _s_g, _s_b;          // Iris / foreground colour
    uint8_t _s_bg_r, _s_bg_g, _s_bg_b; // Background colour
    int _s_x, _s_y;                    // Gaze offset –100 … +100
    bool _new_cmd;

    // ── Rendered / interpolated state  (written by redraw) ───────────────────
    EyeMode _d_mode;
    EyeShape _d_shape;
    uint16_t _d_col, _d_bg_col;
    int _d_cx, _d_cy;
    float _f_cx, _f_cy; // Smoothed gaze position
    float _f_shape;     // –1 = sad │ 0 = neutral │ +1 = happy
    float _f_squint;    //  0 = open              │  1 = closed

    // ── Idle blink state  (FLUJO 1) ───────────────────────────────────────────
    unsigned long _blink_timer;
    uint8_t _blink_phase; // 0 = waiting │ 1 = closing │ 2 = opening

    // ── Drawing helpers ───────────────────────────────────────────────────────
    // Renders the eye shape for the current blend parameters:
    //   t_shape : –1 = sad arc │ 0 = neutral pill │ +1 = happy arc
    //   squint  :  0 = fully open              │  1 = fully closed (blink)
    void drawEyeShape(int cx, int cy,
                      float t_shape, float squint,
                      uint16_t eyeCol, uint16_t bgCol);

    // Draws small white specular highlights; fades with |t_shape|
    void drawHighlight(int cx, int cy, float t_shape, uint16_t irisCol);

    // GC9A01 hardware initialisation sequence
    void initGC9A01();

    // ── Protocol command handlers ─────────────────────────────────────────────
    void handleOnCommand();
    void handleOffCommand();
    void handleFillCommand(const String &command);
    void handleDrawCommand(const String &command);
    void handleMoveCommand(const String &command);

    // ── Low-level SPI helpers  (Port L direct bitmask, Arduino Mega 2560) ────
    // Pins 42–49  →  PL7–PL0 :  mask = _BV(49 – pin)
    inline void CS_LOW() { PORTL &= ~_cs_mask; }
    inline void CS_HIGH() { PORTL |= _cs_mask; }
    inline void DC_LOW() { PORTL &= ~_dc_mask; }
    inline void DC_HIGH() { PORTL |= _dc_mask; }

    void gc_cmd(uint8_t cmd);
    void gc_dat1(uint8_t d);
    void gc_datn(const uint8_t *d, uint8_t n);
    void setWindow(int x0, int y0, int x1, int y1);
    void fillRect(int x0, int y0, int x1, int y1, uint16_t col);

    static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b)
    {
        return ((uint16_t)(r >> 3) << 11) |
               ((uint16_t)(g >> 2) << 5) |
               (b >> 3);
    }
};

#endif // EYE_CONTROLLER_H