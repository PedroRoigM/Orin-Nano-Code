// firmware_mega.ino
// Arduino Mega 2560
// Protocolo: [0x40, CMD, NODE, ...data..., 0x0D]
//
// Componentes:
//   - 3x tiras WS2812B
//   - 2x LCD I2C (direcciones 0x27 y 0x3F)
//   - 2x HC-SR04
//
// Librería necesaria (Arduino IDE Library Manager):
//   - FastLED
//   - LiquidCrystal_I2C (Frank de Brabander)

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <FastLED.h>

// ── WS2812B ───────────────────────────────────────────────────
#define LED_PIN_1     22
#define LED_PIN_2     23
#define LED_PIN_3     24
#define NUM_LEDS       30
#define LED_BRIGHTNESS 50   // 0-255, empieza bajo para no saturar la alimentación

CRGB leds1[NUM_LEDS];
CRGB leds2[NUM_LEDS];
CRGB leds3[NUM_LEDS];

// ── LCD I2C ───────────────────────────────────────────────────
// Si ambas tienen la misma dirección, cambiar el jumper A0 de una
// para que sea 0x3F en lugar de 0x27
LiquidCrystal_I2C lcd1(0x27, 20, 4);
LiquidCrystal_I2C lcd2(0x3F, 20, 4);

// ── HC-SR04 ───────────────────────────────────────────────────
#define TRIG_FRONT 26
#define ECHO_FRONT 27
#define TRIG_BACK  28
#define ECHO_BACK  29

#define ULTRASONIC_INTERVAL 100  // ms entre lecturas

unsigned long last_ultrasonic = 0;

float readDistance(uint8_t trig, uint8_t echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long duration = pulseIn(echo, HIGH, 30000);
  if (duration == 0) return 999.0;
  return duration * 0.0343 / 2.0;
}

// ── Protocolo ─────────────────────────────────────────────────
#define BUF_START 0x40
#define BUF_END   0x0D

#define CMD_LED_COLOR       72
#define CMD_LED_BRIGHTNESS  80
#define CMD_LED_PATTERN     81
#define CMD_LCD_TEXT        82
#define CMD_LCD_CLEAR       85

#define NODE_LED  10
#define NODE_LCD  11

#define MAX_BUF 64
uint8_t buf[MAX_BUF];
uint8_t buf_len  = 0;
bool    receiving = false;

// ── Helpers LED ───────────────────────────────────────────────
void setStripColor(uint8_t target, uint8_t r, uint8_t g, uint8_t b) {
  CRGB color = CRGB(r, g, b);
  if (target == 0 || target == 1) fill_solid(leds1, NUM_LEDS, color);
  if (target == 0 || target == 2) fill_solid(leds2, NUM_LEDS, color);
  if (target == 0 || target == 3) fill_solid(leds3, NUM_LEDS, color);
  FastLED.show();
}

void setStripBrightness(uint8_t target, uint8_t brightness) {
  // Ajusta brillo por tira individualmente si FastLED lo soporta
  // o globalmente como fallback
  FastLED.setBrightness(brightness);
  FastLED.show();
}

// ── Dispatch ──────────────────────────────────────────────────
void handlePacket(uint8_t* data, uint8_t len) {
  if (len < 2) return;
  uint8_t cmd  = data[0];
  uint8_t node = data[1];

  // LED_COLOR: [CMD, NODE_LED, target, r, g, b]
  if (cmd == CMD_LED_COLOR && node == NODE_LED && len >= 6) {
    setStripColor(data[2], data[3], data[4], data[5]);
    return;
  }

  // LED_BRIGHTNESS: [CMD, NODE_LED, target, brightness]
  if (cmd == CMD_LED_BRIGHTNESS && node == NODE_LED && len >= 4) {
    setStripBrightness(data[2], data[3]);
    return;
  }

  // LED_PATTERN: [CMD, NODE_LED, target, pattern_id]
  // Patrones simples — expande según necesites
  if (cmd == CMD_LED_PATTERN && node == NODE_LED && len >= 4) {
    uint8_t pattern = data[3];
    if (pattern == 0) {  // apagado
      setStripColor(data[2], 0, 0, 0);
    } else if (pattern == 4) {  // arcoíris estático de muestra
      fill_rainbow(leds1, NUM_LEDS, 0, 10);
      fill_rainbow(leds2, NUM_LEDS, 0, 10);
      fill_rainbow(leds3, NUM_LEDS, 0, 10);
      FastLED.show();
    }
    return;
  }

  // LCD_TEXT: [CMD, NODE_LCD, line, col, ...ascii...]
  // target lcd: bit 7 de node — usamos data[2] como lcd_id (0=ambas, 1=lcd1, 2=lcd2)
  if (cmd == CMD_LCD_TEXT && node == NODE_LCD && len >= 5) {
    uint8_t lcd_id = data[2];
    uint8_t line   = data[3];  // fila
    uint8_t col    = data[4];  // columna
    char text[21];
    uint8_t text_len = 0;
    for (uint8_t i = 5; i < len && text_len < 20; i++) {
      text[text_len++] = (char)data[i];
    }
    text[text_len] = '\0';

    if (lcd_id == 0 || lcd_id == 1) {
      lcd1.setCursor(col, line);
      lcd1.print(text);
    }
    if (lcd_id == 0 || lcd_id == 2) {
      lcd2.setCursor(col, line);
      lcd2.print(text);
    }
    return;
  }

  // LCD_CLEAR: [CMD, NODE_LCD, lcd_id]
  if (cmd == CMD_LCD_CLEAR && node == NODE_LCD) {
    uint8_t lcd_id = (len >= 3) ? data[2] : 0;
    if (lcd_id == 0 || lcd_id == 1) lcd1.clear();
    if (lcd_id == 0 || lcd_id == 2) lcd2.clear();
    return;
  }
}

// ── Setup ─────────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);

  // LEDs
  FastLED.addLeds<WS2812B, LED_PIN_1, GRB>(leds1, NUM_LEDS);
  FastLED.addLeds<WS2812B, LED_PIN_2, GRB>(leds2, NUM_LEDS);
  FastLED.addLeds<WS2812B, LED_PIN_3, GRB>(leds3, NUM_LEDS);
  FastLED.setBrightness(LED_BRIGHTNESS);
  FastLED.clear(true);

  // LCD
  lcd1.init(); lcd1.backlight(); lcd1.print("LCD1 Ready");
  lcd2.init(); lcd2.backlight(); lcd2.print("LCD2 Ready");

  // Ultrasónico
  pinMode(TRIG_FRONT, OUTPUT); pinMode(ECHO_FRONT, INPUT);
  pinMode(TRIG_BACK,  OUTPUT); pinMode(ECHO_BACK,  INPUT);
}

// ── Loop ──────────────────────────────────────────────────────
void loop() {
  // 1. Parsear paquetes entrantes
  while (Serial.available()) {
    uint8_t b = Serial.read();

    if (b == BUF_START) {
      buf_len   = 0;
      receiving = true;
      continue;
    }

    if (!receiving) continue;

    if (b == BUF_END) {
      handlePacket(buf, buf_len);
      receiving = false;
      buf_len   = 0;
      continue;
    }

    if (buf_len < MAX_BUF) buf[buf_len++] = b;
  }

  // 2. Enviar lecturas ultrasónicas
  unsigned long now = millis();
  if (now - last_ultrasonic >= ULTRASONIC_INTERVAL) {
    last_ultrasonic = now;
    float front = readDistance(TRIG_FRONT, ECHO_FRONT);
    float back  = readDistance(TRIG_BACK,  ECHO_BACK);
    Serial.print(front, 1);
    Serial.print(",");
    Serial.println(back, 1);
  }
}
