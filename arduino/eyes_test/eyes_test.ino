// Buffer RX ampliado: evita que desborde durante el render (~550 ms / frame)
// 960 bytes/s a 9600 baud × 0.6 s = 576 bytes mínimos necesarios
#define SERIAL_RX_BUFFER_SIZE 640

/*
 * eyes_test.ino  —  GC9A01 + Arduino Elegoo Mega 2560
 *
 * Conexiones:
 *   RST→47  CS→48  DC→49  SDA(MOSI)→51  SCL(SCK)→52
 *   VCC→3.3V  GND→GND
 *   Segunda pantalla: CS→46, descomentar PIN_CS_R
 *
 * Protocolo serial (9600 baud, '\n'-terminado):
 *   EYES:EYES_1:<emotion>,<r>,<g>,<b>,<squint>,<wide>
 *   GAZE:EYES_1:<gx>,<gy>   (gx,gy: −100..+100)
 *
 * ── Notas de rendimiento ────────────────────────────────────────────────────
 *  En Mega (16 MHz), cada frame tarda ~500-600 ms (57 600 px × SPI + cómputo).
 *  Por eso:
 *    · SERIAL_RX_BUFFER_SIZE 640  — evita desbordamiento durante el render
 *    · readSerial() entre filas  — vacía el buffer sin interrumpir el stream SPI
 *    · Gaze sin lerp             — posición inmediata, no interpolada
 *    · BLINK_DURATION_MS 1800   — visible en ≥3 frames a ~550 ms/frame
 */

#include <SPI.h>

// ─── Pines ───────────────────────────────────────────────────────────────────
static const uint8_t PIN_RST  = 47;
static const uint8_t PIN_CS_L = 48;
//static const uint8_t PIN_CS_R = 46;
static const uint8_t PIN_DC   = 49;

// ─── Parámetros ──────────────────────────────────────────────────────────────
#define BLINK_DURATION_MS  5000  // largo para garantizar visibilidad incluso con frames lentos
#define BLINK_CLOSE_PCT      30  // 0-30 %: cerrando
#define BLINK_CLOSED_PCT     40  // 30-40 %: cerrado; 40-100 %: abriendo

// ─── Geometría ───────────────────────────────────────────────────────────────
static const int CX           = 120;
static const int CY           = 120;
static const int SCREEN_R     = 118;
static const int SCLERA_R     = 115;
static const int IRIS_BASE_R  =  76;
static const int PUPIL_BASE_R =  36;
static const int LIMBAL_ADD   =   3;
static const int MAX_GAZE_PX  =  30;
static const int CATCHLIGHT_R =   9;

// ─── LUT del párpado ────────────────────────────────────────────────────────
// crv_lut[px] = 14*(1 - ((px-120)/118)²), generada en setup()
// Ahorra la división 32-bit por píxel en el bucle interno.
static int8_t crv_lut[240];

// ─── Estado (actualizado por serial) ────────────────────────────────────────
static uint8_t s_r      = 200;
static uint8_t s_g      = 200;
static uint8_t s_b      = 200;
static int     s_gx     =   0;   // −100..+100
static int     s_gy     =   0;
static int     s_squint =   0;   // 0-100
static int     s_wide   =   0;   // 0-100

// ─── Estado de animación ─────────────────────────────────────────────────────
static int  s_blink_pct    = 100;
static unsigned long blink_start_ms = 0;
static unsigned long next_blink_ms  = 1500;   // primer parpadeo a los 1.5 s

// ─── Helpers ─────────────────────────────────────────────────────────────────
static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
    return ((uint16_t)(r >> 3) << 11) | ((uint16_t)(g >> 2) << 5) | (b >> 3);
}

// ─── SPI bajo nivel ──────────────────────────────────────────────────────────
static void gc_cmd(uint8_t cs, uint8_t cmd) {
    digitalWrite(PIN_DC, LOW);
    digitalWrite(cs, LOW);
    SPI.transfer(cmd);
    digitalWrite(cs, HIGH);
}
static void gc_dat1(uint8_t cs, uint8_t d) {
    digitalWrite(PIN_DC, HIGH);
    digitalWrite(cs, LOW);
    SPI.transfer(d);
    digitalWrite(cs, HIGH);
}
static void gc_dat(uint8_t cs, const uint8_t* d, uint8_t n) {
    digitalWrite(PIN_DC, HIGH);
    digitalWrite(cs, LOW);
    for (uint8_t i = 0; i < n; i++) SPI.transfer(d[i]);
    digitalWrite(cs, HIGH);
}
static void setWindow(uint8_t cs,
                      uint16_t x0, uint16_t y0,
                      uint16_t x1, uint16_t y1) {
    gc_cmd(cs, 0x2A);
    { uint8_t d[]={(uint8_t)(x0>>8),(uint8_t)(x0&0xFF),
                   (uint8_t)(x1>>8),(uint8_t)(x1&0xFF)};
      gc_dat(cs,d,4); }
    gc_cmd(cs, 0x2B);
    { uint8_t d[]={(uint8_t)(y0>>8),(uint8_t)(y0&0xFF),
                   (uint8_t)(y1>>8),(uint8_t)(y1&0xFF)};
      gc_dat(cs,d,4); }
    gc_cmd(cs, 0x2C);
}

// ─── Init GC9A01 ─────────────────────────────────────────────────────────────
static void initGC9A01(uint8_t cs) {
    digitalWrite(PIN_RST,HIGH); delay(50);
    digitalWrite(PIN_RST,LOW);  delay(100);
    digitalWrite(PIN_RST,HIGH); delay(50);

    gc_cmd(cs,0xEF);
    gc_cmd(cs,0xEB); gc_dat1(cs,0x14);
    gc_cmd(cs,0xFE);
    gc_cmd(cs,0xEF);
    gc_cmd(cs,0xEB); gc_dat1(cs,0x14);
    gc_cmd(cs,0x84); gc_dat1(cs,0x40);
    gc_cmd(cs,0x85); gc_dat1(cs,0xFF);
    gc_cmd(cs,0x86); gc_dat1(cs,0xFF);
    gc_cmd(cs,0x87); gc_dat1(cs,0xFF);
    gc_cmd(cs,0x88); gc_dat1(cs,0x0A);
    gc_cmd(cs,0x89); gc_dat1(cs,0x21);
    gc_cmd(cs,0x8A); gc_dat1(cs,0x00);
    gc_cmd(cs,0x8B); gc_dat1(cs,0x80);
    gc_cmd(cs,0x8C); gc_dat1(cs,0x01);
    gc_cmd(cs,0x8D); gc_dat1(cs,0x01);
    gc_cmd(cs,0x8E); gc_dat1(cs,0xFF);
    gc_cmd(cs,0x8F); gc_dat1(cs,0xFF);
    { uint8_t d[]={0x00,0x20};                       gc_cmd(cs,0xB6); gc_dat(cs,d,2); }
    gc_cmd(cs,0x36); gc_dat1(cs,0x08);
    gc_cmd(cs,0x3A); gc_dat1(cs,0x05);
    { uint8_t d[]={0x08,0x08,0x08,0x08};             gc_cmd(cs,0x90); gc_dat(cs,d,4); }
    gc_cmd(cs,0xBD); gc_dat1(cs,0x06);
    gc_cmd(cs,0xBC); gc_dat1(cs,0x00);
    { uint8_t d[]={0x60,0x01,0x04};                  gc_cmd(cs,0xFF); gc_dat(cs,d,3); }
    gc_cmd(cs,0xC3); gc_dat1(cs,0x13);
    gc_cmd(cs,0xC4); gc_dat1(cs,0x13);
    gc_cmd(cs,0xC9); gc_dat1(cs,0x22);
    gc_cmd(cs,0xBE); gc_dat1(cs,0x11);
    { uint8_t d[]={0x10,0x0E};                       gc_cmd(cs,0xE1); gc_dat(cs,d,2); }
    { uint8_t d[]={0x21,0x0C,0x02};                  gc_cmd(cs,0xDF); gc_dat(cs,d,3); }
    { uint8_t d[]={0x45,0x09,0x08,0x08,0x26,0x2A};   gc_cmd(cs,0xF0); gc_dat(cs,d,6); }
    { uint8_t d[]={0x43,0x70,0x72,0x36,0x37,0x6F};   gc_cmd(cs,0xF1); gc_dat(cs,d,6); }
    { uint8_t d[]={0x45,0x09,0x08,0x08,0x26,0x2A};   gc_cmd(cs,0xF2); gc_dat(cs,d,6); }
    { uint8_t d[]={0x43,0x70,0x72,0x36,0x37,0x6F};   gc_cmd(cs,0xF3); gc_dat(cs,d,6); }
    { uint8_t d[]={0x1B,0x0B};                       gc_cmd(cs,0xED); gc_dat(cs,d,2); }
    gc_cmd(cs,0xAE); gc_dat1(cs,0x77);
    gc_cmd(cs,0xCD); gc_dat1(cs,0x63);
    { uint8_t d[]={0x07,0x07,0x04,0x0E,0x0F,0x09,0x07,0x08,0x03};
                                                      gc_cmd(cs,0x70); gc_dat(cs,d,9); }
    gc_cmd(cs,0xE8); gc_dat1(cs,0x34);
    { uint8_t d[]={0x18,0x0D,0x71,0xED,0x70,0x70,0x18,0x0F,0x71,0xEF,0x70,0x70};
                                                      gc_cmd(cs,0x62); gc_dat(cs,d,12); }
    { uint8_t d[]={0x18,0x11,0x71,0xF1,0x70,0x70,0x18,0x13,0x71,0xF3,0x70,0x70};
                                                      gc_cmd(cs,0x63); gc_dat(cs,d,12); }
    { uint8_t d[]={0x28,0x29,0xF1,0x01,0xF1,0x00,0x07};gc_cmd(cs,0x64); gc_dat(cs,d,7); }
    { uint8_t d[]={0x3C,0x00,0xCD,0x67,0x45,0x45,0x10,0x00,0x00,0x00};
                                                      gc_cmd(cs,0x66); gc_dat(cs,d,10); }
    { uint8_t d[]={0x00,0x3C,0x00,0x00,0x00,0x01,0x54,0x10,0x32,0x98};
                                                      gc_cmd(cs,0x67); gc_dat(cs,d,10); }
    { uint8_t d[]={0x10,0x85,0x80,0x00,0x00,0x4E,0x00};gc_cmd(cs,0x74); gc_dat(cs,d,7); }
    { uint8_t d[]={0x3E,0x07};                       gc_cmd(cs,0x98); gc_dat(cs,d,2); }
    gc_cmd(cs,0x35);
    gc_cmd(cs,0x21);
    gc_cmd(cs,0x11); delay(120);
    gc_cmd(cs,0x29); delay(20);
}

// ─── Serial parser ───────────────────────────────────────────────────────────
static char    s_buf[80];
static uint8_t s_buf_len = 0;

static void parseLine(const char* line) {
    const char* p1 = strchr(line, ':');
    if (!p1) return;
    const char* p2 = strchr(p1 + 1, ':');
    if (!p2) return;

    char base[8];
    uint8_t blen = (uint8_t)(p1 - line);
    if (blen == 0 || blen >= sizeof(base)) return;
    memcpy(base, line, blen);
    base[blen] = '\0';

    const char* payload = p2 + 1;

    if (strcmp(base, "EYES") == 0) {
        const char* c1 = strchr(payload, ',');
        if (!c1) return;
        int r, g, b, sq, wd;
        if (sscanf(c1 + 1, "%d,%d,%d,%d,%d", &r, &g, &b, &sq, &wd) != 5) return;
        s_r      = (uint8_t)constrain(r,  0, 255);
        s_g      = (uint8_t)constrain(g,  0, 255);
        s_b      = (uint8_t)constrain(b,  0, 255);
        s_squint = constrain(sq, 0, 100);
        s_wide   = constrain(wd, 0, 100);
        // Parpadeo al cambiar emoción — solo si no hay uno en curso
        // (si lo reseteamos mid-render, el parpadeo nunca termina)
        if (blink_start_ms == 0) {
            next_blink_ms = millis() + 100;
        }
        Serial.println(F("EYES_1:IRIS:ok"));

    } else if (strcmp(base, "GAZE") == 0) {
        int gx, gy;
        if (sscanf(payload, "%d,%d", &gx, &gy) != 2) return;
        s_gx = constrain(gx, -100, 100);
        s_gy = constrain(gy, -100, 100);
        // Sin ACK de GAZE: evitar saturar el canal de vuelta
    }
}

// readSerial se llama tanto en loop() como dentro de drawEye() entre filas.
// Serial.read() es seguro con CS activo (UART es hardware independiente de SPI).
static void readSerial() {
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            if (s_buf_len > 0) {
                s_buf[s_buf_len] = '\0';
                parseLine(s_buf);
                s_buf_len = 0;
            }
        } else if (s_buf_len < (uint8_t)(sizeof(s_buf) - 1)) {
            s_buf[s_buf_len++] = c;
        }
    }
}

// ─── Parpadeo ────────────────────────────────────────────────────────────────
// BLINK_DURATION_MS=1800 → con frames de ~550 ms:
//   frame 0: trigger  → pct=100 (open)
//   frame 1 (+550ms)  → t=30%  → pct=0 (cerrado)   ← visible
//   frame 2 (+1100ms) → t=61%  → pct=35%             ← visible
//   frame 3 (+1650ms) → t=91%  → pct=85%             ← visible
//   frame 4 (+2200ms) → blink terminado, pct=100
static void updateBlink() {
    unsigned long now = millis();
    if (blink_start_ms == 0) {
        if (now >= next_blink_ms) {
            blink_start_ms = now;
            uint16_t rnd = (uint16_t)(now ^ (now >> 8)) % 5001;
            next_blink_ms = now + BLINK_DURATION_MS + 3000UL + rnd;
        }
        s_blink_pct = 100;
        return;
    }
    unsigned long el = now - blink_start_ms;
    if (el >= (unsigned long)BLINK_DURATION_MS) {
        blink_start_ms = 0; s_blink_pct = 100; return;
    }
    int t = (int)(el * 100UL / (unsigned long)BLINK_DURATION_MS);
    if      (t < BLINK_CLOSE_PCT)  s_blink_pct = 100 - t * 100 / BLINK_CLOSE_PCT;
    else if (t < BLINK_CLOSED_PCT) s_blink_pct = 0;
    else                           s_blink_pct = (t - BLINK_CLOSED_PCT) * 100 / (100 - BLINK_CLOSED_PCT);
}

// ─── Render del ojo ──────────────────────────────────────────────────────────
// Optimizaciones:
//   · crv_lut[] pregenerada: elimina la división 32-bit por píxel
//   · Gradiente iris 2 zonas sin bucle: ~55 ciclos/px vs ~640 antes
//   · dy2 precalculado fuera del bucle interno
//   · readSerial() entre filas: buffer nunca desborda en los ~550 ms del render
//   · Gaze sin lerp: posición inmediata (s_gx/s_gy → iris_cx/cy directamente)
static void drawEye(uint8_t cs, bool mirrored) {
    // Gaze directo sin interpolación — máxima respuesta al movimiento
    int gx_off   = (s_gx * MAX_GAZE_PX) / 100;
    int gy_off   = (s_gy * MAX_GAZE_PX) / 100;
    int iris_cx  = CX + gx_off;
    int iris_cy  = CY + gy_off;

    int iris_r   = IRIS_BASE_R   + (s_wide * 12) / 100;
    int pupil_r  = PUPIL_BASE_R  + (s_wide *  8) / 100;
    int limbal_r = iris_r + LIMBAL_ADD;

    // Párpado: squint (emoción) + blink (animación)
    int squint_drop = (s_squint * 90)  / 100;          // 0-90 px
    int blink_drop  = ((100 - s_blink_pct) * 232) / 100; // 0-232 px
    int total_drop  = squint_drop + blink_drop;
    if (total_drop > 234) total_drop = 234;
    int eyelid_base = (CY - 116) + total_drop;

    int cl_cx = iris_cx + (mirrored ? 14 : -14);
    int cl_cy = iris_cy - 14;

    // Cuadrados de radios (evitan sqrt en el bucle)
    int32_t screen_r2 = (int32_t)SCREEN_R  * SCREEN_R;
    int32_t sclera_r2 = (int32_t)SCLERA_R  * SCLERA_R;
    int32_t iris_r2   = (int32_t)iris_r    * iris_r;
    int32_t iris_r2h  = iris_r2 >> 1;        // umbral gradiente interior
    int32_t limbal_r2 = (int32_t)limbal_r   * limbal_r;
    int32_t pupil_r2  = (int32_t)pupil_r    * pupil_r;
    int32_t catch_r2  = (int32_t)CATCHLIGHT_R * CATCHLIGHT_R;

    setWindow(cs, 0, 0, 239, 239);
    digitalWrite(PIN_DC, HIGH);
    digitalWrite(cs, LOW);

    for (int py = 0; py < 240; py++) {
        // Vaciar buffer serial entre filas (UART es independiente de SPI)
        readSerial();

        int dy = py - CY;
        int32_t dy2 = (int32_t)dy * dy;   // precalculado para la fila

        for (int px = 0; px < 240; px++) {
            int dx = px - CX;
            int32_t sd2 = (int32_t)dx * dx + dy2;

            uint16_t col;

            // 1. Fuera de la pantalla circular
            if (sd2 > screen_r2) {
                col = 0x0000;

            // 2. Párpado (LUT pregenerada, sin división por píxel)
            } else if (py < eyelid_base - (int)crv_lut[px]) {
                col = rgb565(20, 16, 14);

            } else {
                int ix = px - iris_cx, iy = py - iris_cy;
                int32_t id2 = (int32_t)ix * ix + (int32_t)iy * iy;

                // 3. Destello (catchlight)
                int cdx = px - cl_cx, cdy = py - cl_cy;
                if ((int32_t)cdx * cdx + (int32_t)cdy * cdy < catch_r2) {
                    col = 0xFFFF;

                // 4. Pupila
                } else if (id2 < pupil_r2) {
                    col = rgb565(10, 8, 12);

                // 5. Iris — gradiente 2 zonas sin bucle
                //    interior (r < 0.71×iris_r): 60% brillo
                //    exterior (r < iris_r):       90% brillo
                } else if (id2 < iris_r2) {
                    uint16_t f256 = (id2 < iris_r2h) ? 154u : 230u;
                    col = rgb565(
                        (uint8_t)((uint16_t)s_r * f256 >> 8),
                        (uint8_t)((uint16_t)s_g * f256 >> 8),
                        (uint8_t)((uint16_t)s_b * f256 >> 8)
                    );

                // 6. Anillo limbal
                } else if (id2 < limbal_r2) {
                    col = rgb565(18, 14, 10);

                // 7. Esclerótica
                } else if (sd2 < sclera_r2) {
                    col = rgb565(242, 241, 238);

                } else {
                    col = 0x0000;
                }
            }

            SPI.transfer((uint8_t)(col >> 8));
            SPI.transfer((uint8_t)(col & 0xFF));
        }
    }

    digitalWrite(cs, HIGH);
}

// ─── Setup ───────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(9600);

    // Generar LUT: crv(px) = 14*(1-((px-120)/118)²), clamped 0-14
    for (int px = 0; px < 240; px++) {
        int32_t dx  = (int32_t)(px - CX);
        int32_t crv = 14L * (13924L - dx * dx) / 13924L;
        crv_lut[px] = (int8_t)constrain((long)crv, 0L, 14L);
    }

    pinMode(PIN_RST,  OUTPUT);
    pinMode(PIN_CS_L, OUTPUT);
    //pinMode(PIN_CS_R, OUTPUT);
    pinMode(PIN_DC,   OUTPUT);
    pinMode(LED_BUILTIN, OUTPUT);

    digitalWrite(PIN_CS_L, HIGH);
    //digitalWrite(PIN_CS_R, HIGH);
    digitalWrite(PIN_DC,   HIGH);

    SPI.begin();
    SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));

    initGC9A01(PIN_CS_L);
    //initGC9A01(PIN_CS_R);

    drawEye(PIN_CS_L, false);
    //drawEye(PIN_CS_R, true);

    Serial.println(F("EYES_1:READY:ok"));
    digitalWrite(LED_BUILTIN, HIGH);  // LED encendido = listo
}

// ─── Loop ────────────────────────────────────────────────────────────────────
void loop() {
    readSerial();
    updateBlink();
    drawEye(PIN_CS_L, false);
    //drawEye(PIN_CS_R, true);
    // Latido: LED alterna cada frame para confirmar que el loop corre
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
}
