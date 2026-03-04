// EyesController.ino

#include "EyesController.h"

// ── Constructor ───────────────────────────────────────────────────────────
EyesController::EyesController(const String &id,
                               int pinCsLeft, int pinCsRight,
                               int pinDc, int pinRst)
    : GeneralController(id),
      // RST = -1: no dejar que begin() lo gestione individualmente.
      // Lo pulsamos manualmente antes de ambos begin() para resetear los
      // dos displays a la vez con un solo flanco.
      _dispLeft(pinCsLeft, pinDc, -1),
      _dispRight(pinCsRight, pinDc, -1),
      _pinRst(pinRst),
      _irisColor(rgb888to565(200, 200, 180)), // blanco cálido tenue — neutral
      _gazeX(0), _gazeY(0),
      _squint(0), _wide(0),
      _needRedraw(true)
{
    // Reset hardware de ambas pantallas a la vez
    hardwareReset(_pinRst);

    // Inicializar cada display (sin nuevo reset, ya que RST = -1)
    _dispLeft.begin();
    _dispRight.begin();

    // Apagar durante la inicialización para evitar artefactos visuales
    _dispLeft.fillScreen(0x0000);
    _dispRight.fillScreen(0x0000);
}

// ── sanityTest ────────────────────────────────────────────────────────────
void EyesController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    // Secuencia R → G → B → estado inicial para verificar ambas pantallas
    const uint16_t colors[] = {0xF800, 0x07E0, 0x001F};
    for (uint16_t c : colors)
    {
        _dispLeft.fillScreen(c);
        _dispRight.fillScreen(c);
        delay(150);
    }

    // Dibujar estado inicial (ojos neutral, mirada al frente)
    redraw();

    Serial.println(F("PASS"));
}

// ── Update ────────────────────────────────────────────────────────────────
// El Coordinator enruta tanto "EYES" como "GAZE" aquí.
// Diferenciamos por el primer carácter del payload:
//   · Letra          → EYES:emotion,r,g,b,squint,wide
//   · Dígito o '-'   → GAZE:gx,gy
void EyesController::Update(const String &message)
{
    if (message.length() == 0)
        return;

    char first = message.charAt(0);
    if (first == '-' || isDigit(first))
        parseGaze(message);
    else
        parseEyes(message);
}

// ── parseEyes ─────────────────────────────────────────────────────────────
// Payload: "neutral,200,200,180,0,0"
//           ^emotion ^r   ^g   ^b ^squint ^wide
// El nombre de la emoción se ignora — los valores numéricos son suficientes.
void EyesController::parseEyes(const String &payload)
{
    // Saltar el nombre de la emoción (hasta la primera coma)
    int i0 = payload.indexOf(',');
    if (i0 < 0)
        return;

    int i1 = payload.indexOf(',', i0 + 1);
    int i2 = payload.indexOf(',', i1 + 1);
    int i3 = payload.indexOf(',', i2 + 1);
    int i4 = payload.indexOf(',', i3 + 1);
    if (i1 < 0 || i2 < 0 || i3 < 0 || i4 < 0)
        return;

    uint8_t r = (uint8_t)payload.substring(i0 + 1, i1).toInt();
    uint8_t g = (uint8_t)payload.substring(i1 + 1, i2).toInt();
    uint8_t b = (uint8_t)payload.substring(i2 + 1, i3).toInt();
    int squint = (int)payload.substring(i3 + 1, i4).toInt();
    int wide = (int)payload.substring(i4 + 1).toInt();

    _irisColor = rgb888to565(r, g, b);
    _squint = constrain(squint, 0, 100);
    _wide = constrain(wide, 0, 100);
    _needRedraw = true;

    sendToSerial(F("IRIS:ok"));
}

// ── parseGaze ─────────────────────────────────────────────────────────────
// Payload: "30,-10"   (gx, gy en rango -100..+100, float×100)
void EyesController::parseGaze(const String &payload)
{
    int comma = payload.indexOf(',');
    if (comma < 0)
        return;

    int gx = payload.substring(0, comma).toInt();
    int gy = payload.substring(comma + 1).toInt();

    // Convertir -100..+100 → -EYE_GAZE_MAX..+EYE_GAZE_MAX px
    _gazeX = constrain(gx * (int)EYE_GAZE_MAX / 100, -(int)EYE_GAZE_MAX, (int)EYE_GAZE_MAX);
    _gazeY = constrain(gy * (int)EYE_GAZE_MAX / 100, -(int)EYE_GAZE_MAX, (int)EYE_GAZE_MAX);
    _needRedraw = true;

    sendToSerial(F("GAZE:ok"));
}

// ── redraw ────────────────────────────────────────────────────────────────
// Llamar en cada iteración de loop(). Solo renderiza si hay cambios.
void EyesController::redraw()
{
    if (!_needRedraw)
        return;
    _needRedraw = false;

    drawEye(_dispLeft, false); // ojo izquierdo — dirección normal
    drawEye(_dispRight, true); // ojo derecho   — espejado en X
}

// ── drawEye ───────────────────────────────────────────────────────────────
void EyesController::drawEye(Adafruit_GC9A01A &disp, bool mirrored)
{
    const uint16_t BLACK = 0x0000;
    const uint16_t WHITE = 0xFFFF;

    int gx = mirrored ? -_gazeX : _gazeX;
    int gy = _gazeY;

    // 1. Fondo negro (la pantalla GC9A01 ya recorta en hardware a círculo,
    //    pero rellenamos el cuadrado por si acaso)
    disp.fillScreen(BLACK);

    // 2. Globo ocular (sclera blanca)
    disp.fillCircle(EYE_CX, EYE_CY, EYE_SCLERA_R, WHITE);

    // 3. Iris — centrado en el punto de mirada
    int irisCX = EYE_CX + gx;
    int irisCY = EYE_CY + gy;

    // Constrain: evitar que el iris sobresalga de la sclera
    float dist = sqrt((float)(gx * gx + gy * gy));
    float maxDist = (float)(EYE_SCLERA_R - EYE_IRIS_R - 3);
    if (dist > 0.5f && dist > maxDist)
    {
        irisCX = EYE_CX + (int)(gx * maxDist / dist);
        irisCY = EYE_CY + (int)(gy * maxDist / dist);
    }
    disp.fillCircle(irisCX, irisCY, EYE_IRIS_R, _irisColor);

    // 4. Pupila (negra, centrada en el iris)
    disp.fillCircle(irisCX, irisCY, EYE_PUPIL_R, BLACK);

    // 5. Reflejo (punto blanco arriba-izquierda del iris)
    disp.fillCircle(irisCX - EYE_IRIS_R / 4,
                    irisCY - EYE_IRIS_R / 4,
                    EYE_IRIS_R / 6, WHITE);

    // 6. Párpado superior (squint)
    //    squint=0 → sin párpado; squint=100 → cubre la mitad del globo
    if (_squint > 0)
    {
        int eyelidH = (_squint * (int)EYE_SCLERA_R) / 100;
        disp.fillRect(0, EYE_CY - EYE_SCLERA_R, 240, eyelidH, BLACK);
    }
}

// ── helpers ───────────────────────────────────────────────────────────────
uint16_t EyesController::rgb888to565(uint8_t r, uint8_t g, uint8_t b)
{
    return ((uint16_t)(r & 0xF8) << 8) | ((uint16_t)(g & 0xFC) << 3) | ((uint16_t)(b >> 3));
}

void EyesController::hardwareReset(int pin)
{
    pinMode(pin, OUTPUT);
    digitalWrite(pin, HIGH);
    delay(10);
    digitalWrite(pin, LOW);
    delay(20);
    digitalWrite(pin, HIGH);
    delay(150); // GC9A01 necesita ≥120 ms tras RST antes de aceptar comandos
}