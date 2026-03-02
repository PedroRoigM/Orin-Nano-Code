#include <Adafruit_NeoPixel.h>

#define PIN 6
#define NUMPIXELS 34
#define BRIGHTNESS 50

Adafruit_NeoPixel strip(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

const int trigPin = 3;
const int echoPin = 2;

float duration, distance;
int incomingByte = 0; // for incoming serial data
// Use uint8_t for RGB (0–255)
uint8_t r, g, b;

void setup()
{
  strip.begin();
  strip.setBrightness(BRIGHTNESS);
  strip.show();

  // Seed random properly
  randomSeed(analogRead(A0));

  // Initialize colors AFTER seeding
  r = random(256);
  g = random(256);
  b = random(256);

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  Serial.begin(9600);
}

// Clamp value safely
uint8_t boundColor(int value)
{
  if (value < 0)
    return 0;
  if (value > 255)
    return 255;
  return value;
}

void randomizeColors()
{
  r = boundColor(r + random(-10, 11));
  g = boundColor(g + random(-10, 11));
  b = boundColor(b + random(-10, 11));
}

void loop()
{

  randomizeColors();

  // Compute color once
  uint32_t color = strip.Color(r, g, b);

  for (uint8_t i = 0; i < NUMPIXELS; i++)
  {
    strip.setPixelColor(i, color);
  }
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  duration = pulseIn(echoPin, HIGH);
  distance = (duration * .0343) / 2;
  Serial.println(distance);
  if (Serial.available() > 0)
  {
    // read the incoming byte:
    incomingByte = Serial.read();

    // say what you got:
    Serial.print("I received: ");
    Serial.println(incomingByte, DEC);
  }
  delay(100);
  strip.show();
  delay(100); // Smooth transition (100ms)
}