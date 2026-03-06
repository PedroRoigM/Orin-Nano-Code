#ifndef EYE_CONTROLLER_H
#define EYE_CONTROLLER_H

#include "GeneralController.h"
#include <SPI.h>

// ─── Geometría (60 FPS Optimized) ───────────────────────────────────────────
#define BALL_R       60     // radio del iris (más grande)
#define BALL_R2    3600L    // 60²
#define PUPIL_R      28     // radio de la pupila
#define PUPIL_R2    784L    // 28²
#define HIGHL_R       5     // radio del punto de luz principal
#define HIGHL_OX     20     // offset X
#define HIGHL_OY     20     // offset Y
#define HIGHL2_R      3     // segundo brillo más pequeño
#define HIGHL2_OX   -10     // abajo a la izquierda
#define HIGHL2_OY   -12
#define MAX_GAZE     45     // Reducido para evitar salirse con ojos grandes
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

    enum PupilShape {
        PUPIL_CIRCLE,
        PUPIL_STAR,
        PUPIL_SMILEY,
        PUPIL_X
    };

private:
    int _pinCs, _pinDc, _pinRst;
    uint8_t _cs_mask, _dc_mask, _rst_mask;
    bool _mirrored;

    // Estado objetivo
    uint8_t _s_r, _s_g, _s_b;
    int _s_gx, _s_gy;
    PupilShape _s_shape;
    bool _new_cmd;

    // Estado actualmente dibujado
    int _d_cx, _d_cy;
    uint8_t _d_r, _d_g, _d_b;
    PupilShape _d_shape;
    float _f_cx, _f_cy; // Interpolación suave

    // Tablas precalculadas
    uint8_t _circ_span[BALL_R + 1];
    uint8_t _pupl_span[PUPIL_R + 1];

    void drawBall(int new_cx, int new_cy, uint16_t irisCol, PupilShape shape);
    void drawHighlight(int cx, int cy, uint16_t irisCol);
    void initGC9A01();
    
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
