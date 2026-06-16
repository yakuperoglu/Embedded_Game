/*
 * main.cpp  (PlatformIO / Arduino framework)
 * -----------------------------------------------------------------------
 * 2 adet Deneyap Kumanda Kolu (analog joystick) -> ESP32-S3 -> USB Seri
 *
 * PC tarafindaki oyun (input_source.py / SerialJoystickInputSource) su
 * satir-bazli protokolu bekler:
 *
 *     x1,y1,b1,x2,y2,b2\n
 *
 *   x,y : 0..4095 ham ADC degeri (12-bit). Oyun bunu -1..1'e cevirir.
 *   b   : 1 = buton basili (ATES), 0 = basili degil.
 *
 * Baud: 115200  (settings.SERIAL_BAUD ile AYNI olmali)
 *
 * Kart: "esp32-s3-devkitc-1" (platformio.ini). Serial, yerlesik USB-C
 * portundan akar (ARDUINO_USB_CDC_ON_BOOT=1).
 * -----------------------------------------------------------------------
 */

#include <Arduino.h>

// ====== PIN HARITASI (ESP32-S3) ======
// Hepsi TEK tarafta (GPIO4-9 ayni uzun kenarda) ve hepsi ADC1 (GPIO1-10).
// Boylece kartin DAR tarafindaki GPIO1/GPIO2'ye hic gerek kalmaz.
// Strapping pinlerden (GPIO0/3/45/46) ve USB pinlerinden (GPIO19/20) kacinildi.
// NOT: Pin degistirirsen sadece burayi guncelle; oyun tarafi etkilenmez.

// --- Joystick 1 (Oyuncu 1 / SOL) ---
const int P1_X  = 4;   // GPIO4  -> ADC1_CH3  (joystick "X")
const int P1_Y  = 5;   // GPIO5  -> ADC1_CH4  (joystick "Y")
const int P1_SW = 6;   // GPIO6  -> buton "SW" (dahili pull-up; basili = HIGH)

// --- Joystick 2 (Oyuncu 2 / SAG) ---
const int P2_X  = 7;   // GPIO7  -> ADC1_CH6  (joystick "X")
const int P2_Y  = 8;   // GPIO8  -> ADC1_CH7  (joystick "Y")
const int P2_SW = 9;   // GPIO9  -> buton "SW" (dahili pull-up; basili = HIGH)

void setup() {
  Serial.begin(115200);

  analogReadResolution(12);          // 0..4095  (oyunun ADC_MAX = 4095 ile uyumlu)
  analogSetAttenuation(ADC_11db);    // tam ~0..3.3V olcum araligi (joystick uclari icin)

  // Butonlar: Deneyap modulunde SW bosta LOW, BASILINCA HIGH okunuyor (test edildi).
  // Pull-up, basili-degil halini stabil tutmak icin birakildi.
  pinMode(P1_SW, INPUT_PULLUP);
  pinMode(P2_SW, INPUT_PULLUP);
}

void loop() {
  // --- Analog eksenler (ham 0..4095) ---
  int x1 = analogRead(P1_X);
  int y1 = analogRead(P1_Y);
  int x2 = analogRead(P2_X);
  int y2 = analogRead(P2_Y);

  // --- Butonlar: bu modulde BASILINCA HIGH. Oyun b=1'i "ates" bekler. ---
  int b1 = (digitalRead(P1_SW) == HIGH) ? 1 : 0;
  int b2 = (digitalRead(P2_SW) == HIGH) ? 1 : 0;

  // --- Tek satir paket: "x1,y1,b1,x2,y2,b2\n" ---
  Serial.printf("%d,%d,%d,%d,%d,%d\n", x1, y1, b1, x2, y2, b2);

  delay(15);   // ~66 paket/sn. Oyun 60 FPS; bu fazlasiyla yeterli ve akici.
}
