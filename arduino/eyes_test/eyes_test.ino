/*
 * eyes_test.ino — GC9A01 + Arduino Elegoo Mega 2560
 *
 * Diseño minimalista: círculo de color sobre fondo negro.
 * El update es un único stream SPI (union bounding box) — sin parpadeo visible.
 *
 * Pines: RST→47  CS→48  DC→49  MOSI→51  SCK→52  VCC→3.3V  GND→GND
 *
 * Protocolo 9600 baud ('\n'-terminado):
 *   EYE:EYES_1:<gx>,<gy>,<r>,<g>,<b>   (gx,gy: −100..+100; r,g,b: 0-255)
 */

#include <SPI.h>

// ─── Pines ───────────────────────────────────────────────────────────────────
#define PIN_RST 46
#define PIN_CS  48
#define PIN_DC  47

// ─── Geometría ───────────────────────────────────────────────────────────────
#define CX          120     // centro pantalla
#define CY          120
#define BALL_R       35     // radio del iris
#define BALL_R2    1225L    // 35²
#define PUPIL_R      14     // radio de la pupila (~40 % del iris)
#define PUPIL_R2    196L    // 14²
#define HIGHL_R       3     // radio del punto de luz (reflejo)
#define HIGHL_OX     12     // offset X del reflejo desde centro del iris
#define HIGHL_OY     12     // offset Y del reflejo (hacia arriba)
#define MAX_GAZE     80     // px máx. desplazamiento desde centro

// ─── Estado objetivo (actualizado por serial) ────────────────────────────────
static uint8_t s_r = 60,  s_g = 150, s_b = 240;
static int     s_gx = 0,  s_gy = 0;
static bool    s_new_cmd = false;   // true cada vez que llega un EYE válido

// ─── Estado actualmente dibujado ─────────────────────────────────────────────
static int     d_cx = CX, d_cy = CY;
static uint8_t d_r  = 0,  d_g  = 0,  d_b  = 0;   // distintos de s_* → fuerza primer draw

// ─── Tablas precalculadas de semiancho por fila ───────────────────────────────
// Calculadas una sola vez en setup(); eliminan la multiplicación 32-bit por píxel.
static uint8_t circ_span[BALL_R  + 1];   // iris
static uint8_t pupl_span[PUPIL_R + 1];   // pupila
// Semiancho del reflejo (radio 3) — fijo, no requiere RAM dinámica
static const uint8_t HIGHL_SPAN[HIGHL_R + 1] = {3, 3, 2, 1};

// ─── Helper RGB565 ───────────────────────────────────────────────────────────
static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
    return ((uint16_t)(r >> 3) << 11) | ((uint16_t)(g >> 2) << 5) | (b >> 3);
}

// ─── SPI bajo nivel ──────────────────────────────────────────────────────────
static void gc_cmd(uint8_t cmd) {
    digitalWrite(PIN_DC, LOW);  digitalWrite(PIN_CS, LOW);
    SPI.transfer(cmd);
    digitalWrite(PIN_CS, HIGH);
}
static void gc_dat1(uint8_t d) {
    digitalWrite(PIN_DC, HIGH); digitalWrite(PIN_CS, LOW);
    SPI.transfer(d);
    digitalWrite(PIN_CS, HIGH);
}
static void gc_datn(const uint8_t* d, uint8_t n) {
    digitalWrite(PIN_DC, HIGH); digitalWrite(PIN_CS, LOW);
    while (n--) SPI.transfer(*d++);
    digitalWrite(PIN_CS, HIGH);
}
static void setWindow(int x0, int y0, int x1, int y1) {
    gc_cmd(0x2A);
    uint8_t xa[] = { 0, (uint8_t)x0, 0, (uint8_t)x1 };
    gc_datn(xa, 4);
    gc_cmd(0x2B);
    uint8_t ya[] = { 0, (uint8_t)y0, 0, (uint8_t)y1 };
    gc_datn(ya, 4);
    gc_cmd(0x2C);
}

// ─── fillRect — para fondo inicial ───────────────────────────────────────────
static void fillRect(int x0, int y0, int x1, int y1, uint16_t col) {
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;
    if (x0 > x1 || y0 > y1) return;
    setWindow(x0, y0, x1, y1);
    uint8_t hi = col >> 8, lo = col & 0xFF;
    uint32_t n = (uint32_t)(x1 - x0 + 1) * (y1 - y0 + 1);
    digitalWrite(PIN_DC, HIGH); digitalWrite(PIN_CS, LOW);
    while (n--) { SPI.transfer(hi); SPI.transfer(lo); }
    digitalWrite(PIN_CS, HIGH);
}

// ─── drawBall — iris + pupila, union bounding box, sin parpadeo ──────────────
// Un solo stream SPI. Por fila: fondo | iris-izq | pupila | iris-der | fondo.
// Filas fuera de la pupila usan solo 3 segmentos (igual que antes).
static void drawBall(int new_cx, int new_cy, uint16_t col) {
    int x0 = min(d_cx, new_cx) - BALL_R - 1;
    int y0 = min(d_cy, new_cy) - BALL_R - 1;
    int x1 = max(d_cx, new_cx) + BALL_R + 1;
    int y1 = max(d_cy, new_cy) + BALL_R + 1;
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;

    uint8_t hi = col >> 8, lo = col & 0xFF;
    setWindow(x0, y0, x1, y1);
    digitalWrite(PIN_DC, HIGH); digitalWrite(PIN_CS, LOW);

    for (int py = y0; py <= y1; py++) {
        int ady = py - new_cy;
        if (ady < 0) ady = -ady;

        if (ady > BALL_R) {
            // Fuera del iris — fila entera negra
            for (int px = x0; px <= x1; px++) {
                SPDR = 0; while (!(SPSR & _BV(SPIF)));
                SPDR = 0; while (!(SPSR & _BV(SPIF)));
            }
        } else {
            uint8_t xs = circ_span[ady];
            int cl = new_cx - xs; if (cl < x0) cl = x0;
            int cr = new_cx + xs; if (cr > x1) cr = x1;

            if (ady <= PUPIL_R) {
                // Fila con pupila: 5 segmentos
                uint8_t ps = pupl_span[ady];
                int pl = new_cx - ps; if (pl < x0) pl = x0;
                int pr = new_cx + ps; if (pr > x1) pr = x1;

                for (int px = x0;    px <  cl; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
                for (int px = cl;    px <  pl; px++) { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
                for (int px = pl;    px <= pr; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
                for (int px = pr+1;  px <= cr; px++) { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
                for (int px = cr+1;  px <= x1; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
            } else {
                // Fila solo con iris: 3 segmentos
                for (int px = x0;   px <  cl; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
                for (int px = cl;   px <= cr; px++) { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
                for (int px = cr+1; px <= x1; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
            }
        }
    }
    digitalWrite(PIN_CS, HIGH);
}

// ─── drawHighlight — punto de luz blanco en el iris ──────────────────────────
// Círculo pequeño (radio 3) en la esquina superior-derecha del iris.
// Llamar DESPUÉS de drawBall; usa el mismo color del iris para el relleno exterior.
static void drawHighlight(int cx, int cy, uint8_t hi, uint8_t lo) {
    int hx = cx + HIGHL_OX;
    int hy = cy - HIGHL_OY;
    int x0 = hx - HIGHL_R, x1 = hx + HIGHL_R;
    int y0 = hy - HIGHL_R, y1 = hy + HIGHL_R;
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;

    setWindow(x0, y0, x1, y1);
    digitalWrite(PIN_DC, HIGH); digitalWrite(PIN_CS, LOW);
    for (int py = y0; py <= y1; py++) {
        int ady = py - hy; if (ady < 0) ady = -ady;
        uint8_t xs = HIGHL_SPAN[ady];
        int hl = hx - xs, hr = hx + xs;
        for (int px = x0; px <= x1; px++) {
            if (px >= hl && px <= hr) {
                SPDR = 0xFF; while (!(SPSR & _BV(SPIF)));
                SPDR = 0xFF; while (!(SPSR & _BV(SPIF)));
            } else {
                SPDR = hi; while (!(SPSR & _BV(SPIF)));
                SPDR = lo; while (!(SPSR & _BV(SPIF)));
            }
        }
    }
    digitalWrite(PIN_CS, HIGH);
}

// ─── Init GC9A01 ─────────────────────────────────────────────────────────────
static void initGC9A01() {
    digitalWrite(PIN_RST, HIGH); delay(50);
    digitalWrite(PIN_RST, LOW);  delay(100);
    digitalWrite(PIN_RST, HIGH); delay(50);

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

// ─── Serial parser ────────────────────────────────────────────────────────────
static char          s_buf[80];
static uint8_t       s_buf_len = 0;
static unsigned long s_last_rx = 0;

static int nextInt(const char*& p) {
    while (*p == ' ') p++;
    bool neg = (*p == '-');
    if (neg) p++;
    int v = 0;
    while (*p >= '0' && *p <= '9') v = v * 10 + (*p++ - '0');
    if (*p == ',') p++;
    return neg ? -v : v;
}

static void parseLine(const char* line) {
    const char* p1 = strchr(line, ':'); if (!p1) return;
    const char* p2 = strchr(p1 + 1, ':'); if (!p2) return;
    const char* payload = p2 + 1;

    if (strncmp(line, "EYE", 3) == 0) {
        // EYE:EYES_1:gx,gy,r,g,b
        const char* c = payload;
        int raw_gx = nextInt(c);
        int raw_gy = nextInt(c);
        int raw_r  = nextInt(c);
        int raw_g  = nextInt(c);
        int raw_b  = nextInt(c);
        s_gx    = constrain(raw_gx, -100, 100);
        s_gy    = constrain(raw_gy, -100, 100);
        s_r     = (uint8_t)constrain(raw_r, 0, 255);
        s_g     = (uint8_t)constrain(raw_g, 0, 255);
        s_b     = (uint8_t)constrain(raw_b, 0, 255);
        s_new_cmd = true;
    }
}

static void processBuffer() {
    if (s_buf_len == 0) return;
    s_buf[s_buf_len] = '\0';
    parseLine(s_buf);
    s_buf_len = 0;
}

static void readSerial() {
    while (Serial.available()) {
        char c = (char)Serial.read();
        s_last_rx = millis();
        if (c == '\n' || c == '\r') {
            processBuffer();
        } else if (s_buf_len < (uint8_t)(sizeof(s_buf) - 1)) {
            s_buf[s_buf_len++] = c;
        }
    }
    if (s_buf_len > 0 && (millis() - s_last_rx) > 80UL) {
        processBuffer();
    }
}

// ─── Setup ───────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(9600);

    // Precalcular semiancho por fila para iris y pupila
    for (uint8_t dy = 0; dy <= BALL_R; dy++) {
        long dy2 = (long)dy * dy;
        circ_span[dy] = (dy2 > BALL_R2)  ? 0 : (uint8_t)sqrt((float)(BALL_R2  - dy2));
    }
    for (uint8_t dy = 0; dy <= PUPIL_R; dy++) {
        long dy2 = (long)dy * dy;
        pupl_span[dy] = (dy2 > PUPIL_R2) ? 0 : (uint8_t)sqrt((float)(PUPIL_R2 - dy2));
    }

    pinMode(PIN_RST, OUTPUT);
    pinMode(PIN_CS,  OUTPUT);
    pinMode(PIN_DC,  OUTPUT);
    pinMode(LED_BUILTIN, OUTPUT);

    digitalWrite(PIN_CS, HIGH);
    digitalWrite(PIN_DC, HIGH);

    SPI.begin();
    SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));

    initGC9A01();
    fillRect(0, 0, 239, 239, 0x0000);

    Serial.println(F("EYES_1:READY:ok"));
    digitalWrite(LED_BUILTIN, HIGH);
}

// ─── Loop ────────────────────────────────────────────────────────────────────
void loop() {
    readSerial();

    if (!s_new_cmd) return;
    s_new_cmd = false;

    int new_cx = CX + (int)((long)s_gx * MAX_GAZE / 100);
    int new_cy = CY + (int)((long)s_gy * MAX_GAZE / 100);

    uint16_t col = rgb565(s_r, s_g, s_b);
    drawBall(new_cx, new_cy, col);
    drawHighlight(new_cx, new_cy, col >> 8, col & 0xFF);

    d_cx = new_cx; d_cy = new_cy;
    d_r  = s_r;    d_g  = s_g;    d_b  = s_b;
}
