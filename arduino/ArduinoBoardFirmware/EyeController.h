#ifndef EYE_CONTROLLER_H
#define EYE_CONTROLLER_H

#include "GeneralController.h"
#include <SPI.h>

// ─── Eye Geometry (60 FPS Optimized) ────────────────────────────────────────
#define EYE_WIDTH    80     // Max width of the eye shape
#define EYE_HEIGHT   100    // Max height of the eye shape
#define MAX_GAZE     50     // Max offset from center
#define EYE_CX       120
#define EYE_CY       120
#define SCREEN_W     240
#define SCREEN_H     240

class EyeController : public GeneralController
{
public:
    EyeController(const String &id, int pinCs, int pinDc, int pinRst, int pinMosi, int pinSclk, bool mirrored = false);

    void sanityTest() override;
    void Update(const String &message) override;
    void redraw();
    void begin();

protected:
    void parseMessage(const String &message) override;

    enum EyeShape {
        SHAPE_NEUTRAL,
        SHAPE_HAPPY,
        SHAPE_SAD
    };

    enum EyeMode {
        MODE_OFF,
        MODE_FILL,
        MODE_DRAW
    };

private:
    int _pinCs, _pinDc, _pinRst;
    uint8_t _cs_mask, _dc_mask, _rst_mask;
    bool _mirrored;

    // Target State
    EyeMode _s_mode;
    EyeShape _s_shape;
    uint8_t _s_r, _s_g, _s_b;           // Foreground/Eye color
    uint8_t _s_bg_r, _s_bg_g, _s_bg_b;  // Background color
    int _s_x, _s_y;                     // Coordinates
    bool _new_cmd;

    // Discovered/Drawn State
    EyeMode _d_mode;
    EyeShape _d_shape;
    uint16_t _d_col;
    uint16_t _d_bg_col;
    int _d_cx, _d_cy;
    float _f_cx, _f_cy; // Smooth interpolation

    void drawEyeRegion(int x0, int y0, int x1, int y1, int icx, int icy, uint16_t eyeCol, uint16_t bgCol, EyeShape shape);
    void initGC9A01();

    // High-level protocol handlers invoked from parseMessage()
    void handleOnCommand();
    void handleOffCommand();
    void handleFillCommand(const String &command);
    void handleDrawCommand(const String &command);
    void handleMoveCommand(const String &command);

    // Low-level SPI helpers (Optimized with bitmasks)
    inline void CS_LOW()  { PORTL &= ~_cs_mask; }
    inline void CS_HIGH() { PORTL |=  _cs_mask; }
    inline void DC_LOW()  { PORTL &= ~_dc_mask; }
    inline void DC_HIGH() { PORTL |=  _dc_mask; }
    
    void gc_cmd(uint8_t cmd);
    void gc_dat1(uint8_t d);
    void gc_datn(const uint8_t* d, uint8_t n);
    void setWindow(int x0, int y0, int x1, int y1);
    void fillRect(int x0, int y0, int x1, int y1, uint16_t col);

    static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
        return ((uint16_t)(r >> 3) << 11) | ((uint16_t)(g >> 2) << 5) | (b >> 3);
    }
};

#endif // EYE_CONTROLLER_H
