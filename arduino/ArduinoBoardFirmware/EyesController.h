// EyesController.h
// ================
// Controlador de las dos pantallas oculares GC9A01 (240×240, SPI).
//
// Se registra bajo los tipos "EYES" y "GAZE" en el Coordinator.
// El Coordinator los enruta al mismo objeto; Update() diferencia
// el comando por el formato del payload:
//   · EYES:<emotion>,<r>,<g>,<b>,<squint>,<wide>  → primer char es letra
//   · GAZE:<gx>,<gy>                               → primer char es dígito o '-'
//
// Respuestas al Jetson:
//   EYES_1:IRIS:ok    (tras actualizar color / morfología)
//   EYES_1:GAZE:ok    (tras actualizar mirada)
//
// Dependencias (Gestor de Librerías):
//   · Adafruit GC9A01A  (by Adafruit)
//   · Adafruit GFX Library

#pragma once
#include <Adafruit_GFX.h>
#include <Adafruit_GC9A01A.h>
#include "GeneralController.h"

// ── Geometría del ojo (px sobre display 240×240) ──────────────────────────
static constexpr uint8_t EYE_SCLERA_R = 95; // radio del globo ocular
static constexpr uint8_t EYE_IRIS_R = 40;   // radio del iris coloreado
static constexpr uint8_t EYE_PUPIL_R = 18;  // radio de la pupila
static constexpr uint8_t EYE_GAZE_MAX = 38; // desplazamiento máx. del iris (px)
static constexpr uint8_t EYE_CX = 120;
static constexpr uint8_t EYE_CY = 120;

class EyesController : public GeneralController
{
public:
    // pinRst puede ser compartido entre ambos displays (se resetean juntos).
    EyesController(const String &id,
                   int pinCsLeft, int pinCsRight,
                   int pinDc, int pinRst);

    void sanityTest();

    // Llamado por el Coordinator para EYES y GAZE.
    void Update(const String &message) override;

    // Llamado explícitamente en loop() — renderiza si hay cambios pendientes.
    void redraw();

private:
    Adafruit_GC9A01A _dispLeft;
    Adafruit_GC9A01A _dispRight;
    int _pinRst;

    // Estado actual del ojo
    uint16_t _irisColor; // RGB565
    int _gazeX;          // −EYE_GAZE_MAX .. +EYE_GAZE_MAX (px)
    int _gazeY;
    int _squint; // 0-100  (float×100 recibido del Jetson)
    int _wide;   // 0-100  (reservado para v2)
    bool _needRedraw;

    void parseEyes(const String &payload);
    void parseGaze(const String &payload);
    void drawEye(Adafruit_GC9A01A &disp, bool mirrored);

    static uint16_t rgb888to565(uint8_t r, uint8_t g, uint8_t b);
    static void hardwareReset(int pin);
};