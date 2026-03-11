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
#define EYE_W        70     // ancho del ojo (cápsula)
#define EYE_H       130     // altura total del ojo
#define EYE_R        35     // radio de las esquinas (EYE_W / 2)
#define EYE_R2     1225L    // 35²
#define EYE_Y_FLAT   30     // (EYE_H - 2*EYE_R) / 2
#define MAX_GAZE     40     // Distancia máxima de movimiento al mirar

// ─── Estado objetivo (actualizado por serial) ────────────────────────────────
static uint8_t s_r = 255, s_g = 255, s_b = 255;
static int     s_gx = 0,  s_gy = 0;
static bool    s_new_cmd = false;   // true cada vez que llega un EYE válido
static unsigned long s_last_serial_task = 0;

// ─── Estado actualmente dibujado ─────────────────────────────────────────────
static int     d_cx = CX, d_cy = CY;
static uint8_t d_r  = 0,  d_g  = 0,  d_b  = 0;   // distintos de s_* → fuerza primer draw

// ─── Tablas precalculadas de semiancho por fila ───────────────────────────────
// Calculadas una sola vez en setup(); eliminan la multiplicación 32-bit por píxel.
static uint8_t eye_span[EYE_Y_FLAT + EYE_R + 1];

// ─── Helper RGB565 ───────────────────────────────────────────────────────────
static inline uint16_t rgb565(uint8_t r, uint8_t g, uint8_t b) {
    return ((uint16_t)(r >> 3) << 11) | ((uint16_t)(g >> 2) << 5) | (b >> 3);
}

// ─── Fast I/O Macros (Mega 2560 Port L) ──────────────────────────────────────
// Pin 48 (CS) -> PL1, Pin 47 (DC) -> PL2, Pin 46 (RST) -> PL3
#define CS_LOW()  (PORTL &= ~_BV(1))
#define CS_HIGH() (PORTL |=  _BV(1))
#define DC_LOW()  (PORTL &= ~_BV(2))
#define DC_HIGH() (PORTL |=  _BV(2))

// ─── SPI bajo nivel (Optimized) ──────────────────────────────────────────────
static void gc_cmd(uint8_t cmd) {
    DC_LOW(); CS_LOW();
    SPDR = cmd; while (!(SPSR & _BV(SPIF)));
    CS_HIGH();
}
static void gc_dat1(uint8_t d) {
    DC_HIGH(); CS_LOW();
    SPDR = d; while (!(SPSR & _BV(SPIF)));
    CS_HIGH();
}
static void gc_datn(const uint8_t* d, uint8_t n) {
    DC_HIGH(); CS_LOW();
    while (n--) {
        SPDR = *d++;
        while (!(SPSR & _BV(SPIF)));
    }
    CS_HIGH();
}
static void setWindow(int x0, int y0, int x1, int y1) {
    gc_cmd(0x2A);
    DC_HIGH(); CS_LOW();
    SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = (uint8_t)x0; while (!(SPSR & _BV(SPIF)));
    SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = (uint8_t)x1; while (!(SPSR & _BV(SPIF)));
    CS_HIGH();

    gc_cmd(0x2B);
    DC_HIGH(); CS_LOW();
    SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = (uint8_t)y0; while (!(SPSR & _BV(SPIF)));
    SPDR = 0; while (!(SPSR & _BV(SPIF))); SPDR = (uint8_t)y1; while (!(SPSR & _BV(SPIF)));
    CS_HIGH();
    
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
    DC_HIGH(); CS_LOW();
    while (n--) {
        SPDR = hi; while (!(SPSR & _BV(SPIF)));
        SPDR = lo; while (!(SPSR & _BV(SPIF)));
    }
    CS_HIGH();
}

// ─── drawEye — cápsula del ojo, union bounding box, sin parpadeo ──────────────
static void drawEye(int new_cx, int new_cy, uint16_t col) {
    int max_y_dist = EYE_Y_FLAT + EYE_R + 1;
    int max_x_dist = EYE_R + 1;
    int x0 = min(d_cx, new_cx) - max_x_dist;
    int y0 = min(d_cy, new_cy) - max_y_dist;
    int x1 = max(d_cx, new_cx) + max_x_dist;
    int y1 = max(d_cy, new_cy) + max_y_dist;
    
    if (x0 < 0) x0 = 0; if (y0 < 0) y0 = 0;
    if (x1 > 239) x1 = 239; if (y1 > 239) y1 = 239;

    uint8_t hi = col >> 8, lo = col & 0xFF;
    
    setWindow(x0, y0, x1, y1);
    DC_HIGH(); CS_LOW();

    for (int py = y0; py <= y1; py++) {
        int ady = py - new_cy;
        if (ady < 0) ady = -ady;

        if (ady > EYE_Y_FLAT + EYE_R) {
            for (int px = x1 - x0 + 1; px > 0; px--) {
                SPDR = 0; while (!(SPSR & _BV(SPIF)));
                SPDR = 0; while (!(SPSR & _BV(SPIF)));
            }
        } else {
            uint8_t xs = eye_span[ady];
            int cl = new_cx - xs; if (cl < x0) cl = x0;
            int cr = new_cx + xs; if (cr > x1) cr = x1;

            for (int px = x0;   px <  cl; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
            for (int px = cl;   px <= cr; px++) { SPDR = hi; while (!(SPSR & _BV(SPIF))); SPDR = lo; while (!(SPSR & _BV(SPIF))); }
            for (int px = cr+1; px <= x1; px++) { SPDR = 0;  while (!(SPSR & _BV(SPIF))); SPDR = 0;  while (!(SPSR & _BV(SPIF))); }
        }
    }
    CS_HIGH();
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
        const char* c = payload;
        int raw_gx = nextInt(c);
        int raw_gy = nextInt(c);
        int raw_r  = nextInt(c);
        int raw_g  = nextInt(c);
        int raw_b  = nextInt(c);
        s_gx    = constrain(-raw_gx, -100, 100);
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
}

// ─── Setup ───────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);

    for (int ady = 0; ady <= EYE_Y_FLAT + EYE_R; ady++) {
        if (ady <= EYE_Y_FLAT) {
            eye_span[ady] = EYE_R;
        } else {
            long dy = ady - EYE_Y_FLAT;
            long dy2 = dy * dy;
            eye_span[ady] = (dy2 > EYE_R2) ? 0 : (uint8_t)sqrt((float)(EYE_R2 - dy2));
        }
    }

    pinMode(PIN_RST, OUTPUT);
    pinMode(PIN_CS,  OUTPUT);
    pinMode(PIN_DC,  OUTPUT);
    pinMode(LED_BUILTIN, OUTPUT);

    digitalWrite(PIN_CS, HIGH); // Will be overridden by port macros later
    digitalWrite(PIN_DC, HIGH);

    SPI.begin();
    SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));

    initGC9A01();
    fillRect(0, 0, 239, 239, 0x0000);

    Serial.println(F("EYES_1:READY:ok"));
    digitalWrite(LED_BUILTIN, HIGH);
}

// ─── Loop (High Frequency) ───────────────────────────────────────────────────
static float f_cx = CX, f_cy = CY;

void loop() {
    // Lectura constante sin bloqueos
    readSerial();

    // Actualización de posición con suavizado (Interpolación)
    int target_cx = CX + (int)((long)s_gx * MAX_GAZE / 100);
    int target_cy = CY + (int)((long)s_gy * MAX_GAZE / 100);
    
    // Suavizado para 60 FPS visuales
    f_cx += ((float)target_cx - f_cx) * 0.3f;
    f_cy += ((float)target_cy - f_cy) * 0.3f;
    
    int icx = (int)f_cx;
    int icy = (int)f_cy;

    if (icx != d_cx || icy != d_cy || s_new_cmd) {
        s_new_cmd = false;
        uint16_t col = rgb565(s_r, s_g, s_b);
        drawEye(icx, icy, col);
        d_cx = icx; d_cy = icy;
        d_r = s_r; d_g = s_g; d_b = s_b;
    }
}


