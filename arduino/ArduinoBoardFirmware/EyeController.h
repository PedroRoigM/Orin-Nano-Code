#ifndef EYE_CONTROLLER_H
#define EYE_CONTROLLER_H

#include "GeneralController.h"
#include <SPI.h>

// ─── Geometría (matching eyes_test.ino) ──────────────────────────────────────
#define BALL_R       35     // radio del iris
#define BALL_R2    1225L    // 35²
#define PUPIL_R      14     // radio de la pupila (~40 % del iris)
#define PUPIL_R2    196L    // 14²
#define HIGHL_R       3     // radio del punto de luz (reflejo)
#define HIGHL_OX     12     // offset X del reflejo desde centro del iris
#define HIGHL_OY     12     // offset Y del reflejo (hacia arriba)
#define MAX_GAZE     80     // px máx. desplazamiento desde centro
#define EYE_CX      120
#define EYE_CY      120

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

private:
    int _pinCs, _pinDc, _pinRst;
    bool _mirrored;

    // Estado objetivo
    uint8_t _s_r, _s_g, _s_b;
    int _s_gx, _s_gy;
    bool _new_cmd;

    // Estado actualmente dibujado
    int _d_cx, _d_cy;
    uint8_t _d_r, _d_g, _d_b;

    // Tablas precalculadas
    uint8_t _circ_span[BALL_R + 1];
    uint8_t _pupl_span[PUPIL_R + 1];

    void drawBall(int new_cx, int new_cy, uint16_t col);
    void drawHighlight(int cx, int cy, uint8_t hi, uint8_t lo);
    void initGC9A01();
    
    // Low-level SPI helpers
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
