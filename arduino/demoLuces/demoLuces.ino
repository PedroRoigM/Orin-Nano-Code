#include <LiquidCrystal.h> // Se incluye la librería [cite: 363]

// Definición de los pines (mantengo los que usaste en tu código original)
#define pin_RS 3
#define pin_EN 2
#define pin_D4 4
#define pin_D5 5
#define pin_D6 6
#define pin_D7 7

// Se crea el objeto pantalla [cite: 366]
LiquidCrystal pantalla(pin_RS, pin_EN, pin_D4, pin_D5, pin_D6, pin_D7);

// --- Anexo: Crear un carácter personalizado ---
// Se puede crear una matriz de 8x5 para una cara sonriente [cite: 386, 387]
byte emoti = 1; // Cuidado con usar el 0 directamente [cite: 388]
byte mat_emoti[8] = { // [cite: 389]
  B00000, // [cite: 390]
  B10001, // [cite: 391]
  B00000, // [cite: 392]
  B00000, // [cite: 393]
  B10001, // [cite: 394]
  B01110, // [cite: 395]
  B00000, // [cite: 396]
  B00000  // Completando los 8 elementos
};

void setup() {
  // Pantalla de 16 columnas y 2 filas [cite: 369]
  pantalla.begin(16, 2);

  // Creamos el carácter en la memoria de la pantalla [cite: 407]
  pantalla.createChar(emoti, mat_emoti);

  // Imprimimos un saludo [cite: 370]
  pantalla.print("Hola Mundo");
  
  // Posiciona el cursor en la columna 0, fila 1 [cite: 332]
  // Ojo, la numeración es de 0 a 15 en columnas y de 0 a 1 en filas. [cite: 334]
  pantalla.setCursor(0, 1);
  pantalla.print("Iniciando ");
  pantalla.write(emoti); // Imprimimos el carácter personalizado [cite: 407]
  
  delay(3000); // Esperamos 3 segundos para que se lea el mensaje
  pantalla.clear(); // Limpiamos la pantalla antes de ir al loop principal
}

void loop() {
  // Por defecto empieza en posición 0,0 [cite: 335]
  pantalla.setCursor(0, 0);
  pantalla.print("Pantalla Activa");
  
  // Escribimos en la segunda fila
  pantalla.setCursor(0, 1);
  pantalla.print("Segundos: ");
  // print() admite formatos como int o long [cite: 243]
  pantalla.print(millis() / 1000); 
  
  delay(1000);
}