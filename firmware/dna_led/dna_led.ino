// DNA accessory: 24 x XL-1010RGBC-WS2812B on one data line (XIAO nRF52840, D6/TX -> R1 100 ohm -> U2.DIN).
// Chain order = reference order: pixel 0 = U2, pixel 1 = U3, ... pixel 23 = U25. Pair k = pixels 2k and 2k+1.
// Needs the "Adafruit NeoPixel" library and the Seeed nRF52 board package (use the D6 macro, not a bare 6).
//
// LED power: USB (5 V through D2) when a cable is present, otherwise the battery through the MT3608B boost converter
// (5.0 V); the hardware switches between them. Not compiled or flashed in this session.
//
// Bring-up order (review item 06): 1) walk one pixel at low brightness to prove all 24 stages,
// 2) light the 12 pairs two at a time, 3) only then raise BRIGHTNESS. Measure current and the
// farthest LED's VDD before going above ~25 % (full white is about 0.37 A @ 5 V: USB, or about 0.7 A from a 3.0 V cell via the boost).
#include <Adafruit_NeoPixel.h>
#include <nrf.h>

#define LED_PIN D6
#define N_LEDS 24
#define BRIGHTNESS 40            // 0..255, limit used for every colour; raise only after measuring


Adafruit_NeoPixel strip(N_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);  // GRB order, 800 kHz (datasheet p.7 / p.11)

// 5'-ATG GCA TCG TAA-3' as drawn on the silkscreen; strand B is the complement.
const char SEQ[] = "ATGGCATCGTAA";

uint32_t baseColour(char b) {
  switch (b) {
    case 'A': return strip.Color(0, BRIGHTNESS, 0);                         // green
    case 'T': return strip.Color(BRIGHTNESS, 0, 0);                         // red
    case 'G': return strip.Color(0, 0, BRIGHTNESS);                         // blue
    default:  return strip.Color(BRIGHTNESS, BRIGHTNESS / 2, 0);            // C: amber
  }
}

char complement(char b) {
  return b == 'A' ? 'T' : b == 'T' ? 'A' : b == 'G' ? 'C' : 'G';
}

void showPairs(int count) {   // lights the first `count` pairs
  strip.clear();
  for (int k = 0; k < count && k < 12; k++) {
    strip.setPixelColor(2 * k,     baseColour(SEQ[k]));              // first LED of the pair
    strip.setPixelColor(2 * k + 1, baseColour(complement(SEQ[k])));  // second LED of the pair
  }
  strip.show();
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  delay(100);                  // let the LED supply settle (USB, or the battery boost converter starting) before any data is sent
  strip.begin();
  strip.clear();
  strip.show();

  // 1) one pixel at a time: every one of the 24 stages must light in order.
  for (int i = 0; i < N_LEDS; i++) {
    strip.clear();
    strip.setPixelColor(i, strip.Color(10, 10, 10));
    strip.show();
    delay(150);
  }
  strip.clear();
  strip.show();
}

void loop() {
  // 2) grow the sequence pair by pair, hold, then restart.
  for (int k = 1; k <= 12; k++) {
    showPairs(k);
    delay(250);
  }
  delay(2000);
}
