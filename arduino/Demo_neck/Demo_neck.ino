/*
  Demo_neck.ino
  =============
  Sketch de prueba para el controlador de cuello (pan/tilt) del robot médico.

  Recibe comandos de CameraServoController a través del puerto serial y mueve
  dos servos para verificar que el protocolo y el comportamiento son correctos.

  PROTOCOLO (texto, nuevo firmware):
      NECK:SRV_1:<pan>,<tilt>\n
      ej. "NECK:SRV_1:90,90\n"  → centro
          "NECK:SRV_1:78,85\n"  → mirando ligeramente a la derecha y abajo

  WIRING (Arduino Uno / Mega):
      Servo PAN  (horizontal) → pin 9
      Servo TILT (vertical)   → pin 10
      Cada servo: VCC → 5 V, GND → GND, signal → pin definido arriba.

  BAUD RATE: 9600  (ajustar si el firmware principal usa otro valor)

  RESPUESTA:
      Para cada comando recibido el sketch imprime en Serial:
          ACK NECK pan=<p> tilt=<t>
      Para comandos malformados:
          ERR <línea recibida>

  PRUEBA DESDE PYTHON (tensor_rt_computer.py en modo PC):
      Ejecutar el pipeline — los comandos aparecerán en la terminal como:
          [SERIAL →] NECK:SRV_1:88,91
      Conectar el Arduino y abrir el Monitor Serie para ver los ACKs.
*/

#include <Servo.h>

// ── Pines ────────────────────────────────────────────────────────────────────
static const int PIN_PAN  = 9;
static const int PIN_TILT = 10;

// ── Límites mecánicos (mismos que CameraServoController en Python) ────────────
static const int PAN_MIN  =  70;  static const int PAN_MAX  = 110;
static const int TILT_MIN =  80;  static const int TILT_MAX = 100;
static const int PAN_CENTER  = 90;
static const int TILT_CENTER = 90;

// ── Suavizado en firmware ─────────────────────────────────────────────────────
// El Python ya envía posiciones suavizadas, pero añadimos un paso de lerp
// en el Arduino para absorber cualquier salto brusco residual.
// Ajustar LERP_STEPS para más o menos suavidad (1 = sin suavizado).
static const int   LERP_STEPS    = 3;    // pasos intermedios por comando
static const int   LERP_DELAY_MS = 8;    // ms entre pasos (~24 ms por movimiento)

// ── Estado ───────────────────────────────────────────────────────────────────
Servo servoPan;
Servo servoTilt;

int currentPan  = PAN_CENTER;
int currentTilt = TILT_CENTER;

// Buffer de línea serial
static char   lineBuf[64];
static uint8_t lineLen = 0;

// ── Setup ────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(9600);
  servoPan.attach(PIN_PAN);
  servoTilt.attach(PIN_TILT);

  // Centrar al arrancar
  servoPan.write(PAN_CENTER);
  servoTilt.write(TILT_CENTER);

  Serial.println("NECK_DEMO ready. Waiting for NECK:SRV_1:<pan>,<tilt>");
}

// ── Loop ─────────────────────────────────────────────────────────────────────
void loop() {
  // Leer bytes hasta '\n'
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (lineLen > 0) {
        lineBuf[lineLen] = '\0';
        processLine(lineBuf);
        lineLen = 0;
      }
    } else if (lineLen < sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = c;
    }
  }
}

// ── Procesar una línea completa ───────────────────────────────────────────────
void processLine(const char* line) {
  // Formato esperado: "NECK:SRV_1:<pan>,<tilt>"
  // Buscar el prefijo "NECK:SRV_1:"
  const char* prefix = "NECK:SRV_1:";
  if (strncmp(line, prefix, strlen(prefix)) != 0) {
    Serial.print("ERR ");
    Serial.println(line);
    return;
  }

  const char* payload = line + strlen(prefix);  // "<pan>,<tilt>"
  char* comma = strchr(payload, ',');
  if (comma == NULL) {
    Serial.print("ERR ");
    Serial.println(line);
    return;
  }

  int pan  = atoi(payload);
  int tilt = atoi(comma + 1);

  // Aplicar límites de seguridad
  pan  = constrain(pan,  PAN_MIN,  PAN_MAX);
  tilt = constrain(tilt, TILT_MIN, TILT_MAX);

  // Mover con suavizado
  moveSmooth(pan, tilt);

  Serial.print("ACK NECK pan=");
  Serial.print(currentPan);
  Serial.print(" tilt=");
  Serial.println(currentTilt);
}

// ── Movimiento suave con interpolación lineal ─────────────────────────────────
void moveSmooth(int targetPan, int targetTilt) {
  for (int step = 1; step <= LERP_STEPS; step++) {
    int p = currentPan  + (targetPan  - currentPan)  * step / LERP_STEPS;
    int t = currentTilt + (targetTilt - currentTilt) * step / LERP_STEPS;
    servoPan.write(p);
    servoTilt.write(t);
    delay(LERP_DELAY_MS);
  }
  currentPan  = targetPan;
  currentTilt = targetTilt;
}
