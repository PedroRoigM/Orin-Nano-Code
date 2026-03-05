/*
 * gc9a01_connection_test.ino
 * ==========================
 * Test mínimo de conexión GC9A01 — sin protocolo serial, sin ojos.
 * Rellena la pantalla con colores sólidos y patrones aleatorios.
 *
 * Conexiones (Arduino Elegoo Mega 2560):
 *   RST → 47  |  CS → 48  |  DC → 49
 *   SDA → 51 (MOSI)  |  SCL → 52 (SCK)
 *   VCC → 3.3 V  |  GND → GND
 *
 * Si ves colores cambiando en la pantalla → conexión OK.
 * Si la pantalla queda blanca/negra/estática → revisar cableado.
 */

#include <SPI.h>

#define PIN_RST  47
#define PIN_CS   48
#define PIN_DC   49

// ─── SPI bajo nivel ──────────────────────────────────────────────────────────
static void writeCmd(uint8_t cmd) {
    digitalWrite(PIN_DC, LOW);
    digitalWrite(PIN_CS, LOW);
    SPI.transfer(cmd);
    digitalWrite(PIN_CS, HIGH);
}

static void writeData(uint8_t d) {
    digitalWrite(PIN_DC, HIGH);
    digitalWrite(PIN_CS, LOW);
    SPI.transfer(d);
    digitalWrite(PIN_CS, HIGH);
}

static void writeBuf(const uint8_t* buf, uint16_t len) {
    digitalWrite(PIN_DC, HIGH);
    digitalWrite(PIN_CS, LOW);
    for (uint16_t i = 0; i < len; i++) SPI.transfer(buf[i]);
    digitalWrite(PIN_CS, HIGH);
}

// ─── Init GC9A01 ─────────────────────────────────────────────────────────────
static void initDisplay() {
    digitalWrite(PIN_RST, HIGH); delay(50);
    digitalWrite(PIN_RST, LOW);  delay(100);
    digitalWrite(PIN_RST, HIGH); delay(50);

    writeCmd(0xEF);
    writeCmd(0xEB); writeData(0x14);
    writeCmd(0xFE);
    writeCmd(0xEF);
    writeCmd(0xEB); writeData(0x14);
    writeCmd(0x84); writeData(0x40);
    writeCmd(0x85); writeData(0xFF);
    writeCmd(0x86); writeData(0xFF);
    writeCmd(0x87); writeData(0xFF);
    writeCmd(0x88); writeData(0x0A);
    writeCmd(0x89); writeData(0x21);
    writeCmd(0x8A); writeData(0x00);
    writeCmd(0x8B); writeData(0x80);
    writeCmd(0x8C); writeData(0x01);
    writeCmd(0x8D); writeData(0x01);
    writeCmd(0x8E); writeData(0xFF);
    writeCmd(0x8F); writeData(0xFF);
    writeCmd(0xB6); writeData(0x00); writeData(0x20);
    writeCmd(0x36); writeData(0x08);   // Memory Access
    writeCmd(0x3A); writeData(0x05);   // RGB565
    writeCmd(0x90); writeData(0x08); writeData(0x08); writeData(0x08); writeData(0x08);
    writeCmd(0xBD); writeData(0x06);
    writeCmd(0xBC); writeData(0x00);
    writeCmd(0xFF); writeData(0x60); writeData(0x01); writeData(0x04);
    writeCmd(0xC3); writeData(0x13);
    writeCmd(0xC4); writeData(0x13);
    writeCmd(0xC9); writeData(0x22);
    writeCmd(0xBE); writeData(0x11);
    writeCmd(0xE1); writeData(0x10); writeData(0x0E);
    writeCmd(0xDF); writeData(0x21); writeData(0x0C); writeData(0x02);
    writeCmd(0xF0); writeData(0x45); writeData(0x09); writeData(0x08); writeData(0x08); writeData(0x26); writeData(0x2A);
    writeCmd(0xF1); writeData(0x43); writeData(0x70); writeData(0x72); writeData(0x36); writeData(0x37); writeData(0x6F);
    writeCmd(0xF2); writeData(0x45); writeData(0x09); writeData(0x08); writeData(0x08); writeData(0x26); writeData(0x2A);
    writeCmd(0xF3); writeData(0x43); writeData(0x70); writeData(0x72); writeData(0x36); writeData(0x37); writeData(0x6F);
    writeCmd(0xED); writeData(0x1B); writeData(0x0B);
    writeCmd(0xAE); writeData(0x77);
    writeCmd(0xCD); writeData(0x63);
    writeCmd(0x70); writeData(0x07); writeData(0x07); writeData(0x04); writeData(0x0E); writeData(0x0F); writeData(0x09); writeData(0x07); writeData(0x08); writeData(0x03);
    writeCmd(0xE8); writeData(0x34);
    writeCmd(0x62); writeData(0x18); writeData(0x0D); writeData(0x71); writeData(0xED); writeData(0x70); writeData(0x70); writeData(0x18); writeData(0x0F); writeData(0x71); writeData(0xEF); writeData(0x70); writeData(0x70);
    writeCmd(0x63); writeData(0x18); writeData(0x11); writeData(0x71); writeData(0xF1); writeData(0x70); writeData(0x70); writeData(0x18); writeData(0x13); writeData(0x71); writeData(0xF3); writeData(0x70); writeData(0x70);
    writeCmd(0x64); writeData(0x28); writeData(0x29); writeData(0xF1); writeData(0x01); writeData(0xF1); writeData(0x00); writeData(0x07);
    writeCmd(0x66); writeData(0x3C); writeData(0x00); writeData(0xCD); writeData(0x67); writeData(0x45); writeData(0x45); writeData(0x10); writeData(0x00); writeData(0x00); writeData(0x00);
    writeCmd(0x67); writeData(0x00); writeData(0x3C); writeData(0x00); writeData(0x00); writeData(0x00); writeData(0x01); writeData(0x54); writeData(0x10); writeData(0x32); writeData(0x98);
    writeCmd(0x74); writeData(0x10); writeData(0x85); writeData(0x80); writeData(0x00); writeData(0x00); writeData(0x4E); writeData(0x00);
    writeCmd(0x98); writeData(0x3E); writeData(0x07);
    writeCmd(0x35);          // Tearing ON
    writeCmd(0x21);          // Inversion ON
    writeCmd(0x11); delay(120);  // Sleep out
    writeCmd(0x29); delay(20);   // Display ON
}

// ─── Relleno de pantalla ─────────────────────────────────────────────────────
// Rellena los 240×240 px con un color RGB565 sólido.
static void fillScreen(uint16_t color) {
    // Ventana completa
    writeCmd(0x2A);
    writeData(0x00); writeData(0x00); writeData(0x00); writeData(0xEF);
    writeCmd(0x2B);
    writeData(0x00); writeData(0x00); writeData(0x00); writeData(0xEF);
    writeCmd(0x2C);

    uint8_t hi = color >> 8;
    uint8_t lo = color & 0xFF;

    digitalWrite(PIN_DC, HIGH);
    digitalWrite(PIN_CS, LOW);
    for (uint32_t i = 0; i < 240UL * 240UL; i++) {
        SPI.transfer(hi);
        SPI.transfer(lo);
    }
    digitalWrite(PIN_CS, HIGH);
}

// Convierte R8 G8 B8 → RGB565
static inline uint16_t rgb(uint8_t r, uint8_t g, uint8_t b) {
    return ((uint16_t)(r >> 3) << 11) | ((uint16_t)(g >> 2) << 5) | (b >> 3);
}

// ─── Setup ───────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(9600);
    Serial.println(F("GC9A01 connection test — init..."));

    pinMode(PIN_RST, OUTPUT);
    pinMode(PIN_CS,  OUTPUT);
    pinMode(PIN_DC,  OUTPUT);
    pinMode(LED_BUILTIN, OUTPUT);

    digitalWrite(PIN_CS, HIGH);
    digitalWrite(PIN_DC, HIGH);

    SPI.begin();
    SPI.beginTransaction(SPISettings(8000000, MSBFIRST, SPI_MODE0));

    initDisplay();

    Serial.println(F("Init OK — pintando colores..."));
    digitalWrite(LED_BUILTIN, HIGH);
}

// ─── Loop ────────────────────────────────────────────────────────────────────
// Ciclo de colores sólidos con 1 s de pausa entre cada uno.
// Si ves los colores cambiando en la pantalla, la conexión SPI es correcta.

static const uint16_t COLORS[] = {
    0xF800,  // Rojo
    0x07E0,  // Verde
    0x001F,  // Azul
    0xFFFF,  // Blanco
    0x0000,  // Negro
    0xFFE0,  // Amarillo
    0xF81F,  // Magenta
    0x07FF,  // Cian
};
static const char* COLOR_NAMES[] = {
    "ROJO", "VERDE", "AZUL", "BLANCO",
    "NEGRO", "AMARILLO", "MAGENTA", "CIAN"
};
static const uint8_t N_COLORS = sizeof(COLORS) / sizeof(COLORS[0]);
static uint8_t color_idx = 0;

void loop() {
    uint16_t c = COLORS[color_idx];

    fillScreen(c);

    Serial.print(F("Pantalla: "));
    Serial.println(COLOR_NAMES[color_idx]);

    // LED parpadea una vez por color para confirmar que el loop corre
    digitalWrite(LED_BUILTIN, LOW);  delay(100);
    digitalWrite(LED_BUILTIN, HIGH); delay(900);

    color_idx = (color_idx + 1) % N_COLORS;
}
