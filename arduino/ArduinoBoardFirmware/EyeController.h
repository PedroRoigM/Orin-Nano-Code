#include "GeneralController.h"

// ─── Screen geometry ─────────────────────────────────────────────────────────
#define EYE_SCREEN_W 240
#define EYE_SCREEN_H 240
#define EYE_CX 120 // screen centre
#define EYE_CY 120

// ─── Capsule geometry ────────────────────────────────────────────────────────
#define EYE_W 70      // capsule width
#define EYE_H 130     // capsule total height
#define EYE_R 35      // corner radius  (= EYE_W / 2)
#define EYE_R2 1225L  // EYE_R²
#define EYE_Y_FLAT 30 // (EYE_H − 2×EYE_R) / 2
#define EYE_SPAN_SIZE (EYE_Y_FLAT + EYE_R + 1)

#define EYE_MAX_GAZE 40 // max pixel offset for gaze

class EyeController : public GeneralController
{
public:
    EyeController(const String &id,
                  int pinCs, int pinDc, int pinRst,
                  int pinMosi, int pinSclk);

    void begin();
    void sanityTest() override;
    void Update(const String &message) override;

    // Call every loop() iteration for smooth gaze interpolation.
    void redraw();

protected:
    void parseMessage(const String &message) override;

private:
    // ── Pin numbers ──────────────────────────────────────────────────────────
    int _pinCs, _pinDc, _pinRst, _pinMosi, _pinSclk;

    // ── Display state ────────────────────────────────────────────────────────
    bool _on;

    // Target values (set by commands)
    uint8_t _r, _g, _b;       // eye colour
    uint8_t _bgR, _bgG, _bgB; // background colour
    int _gx, _gy;             // gaze target  −100..+100

    // Smooth interpolation state
    float _fCx, _fCy; // floating-point current centre

    // Last-drawn state (used to decide when a redraw is needed)
    int _dCx, _dCy;
    uint8_t _dR, _dG, _dB;
    uint8_t _dBgR, _dBgG, _dBgB;
    bool _dirty; // force redraw on next call

    // Pre-computed half-width lookup per row (avoids per-pixel sqrt in loop)
    uint8_t _eyeSpan[EYE_SPAN_SIZE];

    // ── Low-level SPI / GC9A01 helpers ───────────────────────────────────────
    void initGC9A01();

    inline void csLow() { digitalWrite(_pinCs, LOW); }
    inline void csHigh() { digitalWrite(_pinCs, HIGH); }
    inline void dcLow() { digitalWrite(_pinDc, LOW); }
    inline void dcHigh() { digitalWrite(_pinDc, HIGH); }

    void gcCmd(uint8_t cmd);
    void gcDat1(uint8_t d);
    void gcDatN(const uint8_t *d, uint8_t n);
    void setWindow(int x0, int y0, int x1, int y1);
    void spiWrite(uint8_t b);

    // ── Draw primitives ───────────────────────────────────────────────────────
    void fillScreen(uint16_t colour);
    void fillRect(int x0, int y0, int x1, int y1, uint16_t colour);
    void drawEye(int newCx, int newCy, uint16_t eyeCol, uint16_t bgCol);

    // ── Command handlers ──────────────────────────────────────────────────────
    void handleCmdOn();
    void handleCmdOff();
    void handleCmdFill(const String &payload);
    void handleCmdDraw(const String &payload);
    void handleCmdMove(const String &payload);

    // ── Helpers ───────────────────────────────────────────────────────────────
    static uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b);
    static int nextInt(const char *&p);
};
