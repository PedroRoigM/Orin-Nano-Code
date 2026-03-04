#ifndef EYE_CONTROLLER_H
#define EYE_CONTROLLER_H

#include <Adafruit_GFX.h>
#include <Adafruit_GC9A01A.h>
#include "GeneralController.h"

// ── Eye Geometry (px on 240x240 display) ──────────────────────────
static constexpr uint8_t EYE_SCLERA_R = 95; // sclera radius
static constexpr uint8_t EYE_IRIS_R = 40;   // iris radius
static constexpr uint8_t EYE_PUPIL_R = 18;  // pupil radius
static constexpr uint8_t EYE_GAZE_MAX = 38; // max gaze offset (px)
static constexpr uint8_t EYE_CX = 120;
static constexpr uint8_t EYE_CY = 120;

class EyeController : public GeneralController
{
public:
    EyeController(const String &id, int pinCs, int pinDc, int pinRst, bool mirrored = false);

    void sanityTest();
    void Update(const String &message) override;
    void redraw();

protected:
    void parseMessage(const String &message) override;

private:
    Adafruit_GC9A01A _disp;
    int _pinRst;
    bool _mirrored;

    // Eye state
    uint16_t _irisColor; // RGB565
    int _gazeX;          // -EYE_GAZE_MAX .. +EYE_GAZE_MAX (px)
    int _gazeY;
    int _squint;         // 0-100
    int _wide;           // 0-100
    bool _needRedraw;

    void parseEyes(const String &payload);
    void parseGaze(const String &payload);
    void drawEye();

    static uint16_t rgb888to565(uint8_t r, uint8_t g, uint8_t b);
    static void hardwareReset(int pin);
};

#endif // EYE_CONTROLLER_H
