// DNA accessory console firmware: 24 x XL-1010RGBC-WS2812B on one data line
// (XIAO nRF52840, D6/TX -> R1 100 ohm -> U2.DIN), driven by text commands over USB serial.
//
// Chain order = reference order: pixel 0 = U2, pixel 1 = U3, ... pixel 23 = U25.
// Pair k = pixels 2k (strand A) and 2k+1 (strand B). Codon c = pairs 3c..3c+2 (pixels 6c..6c+5).
// The web console (index.html in ../../) sends frames (24 x RRGGBB) and settings; this sketch only plays them.
// Protocol: one ASCII command per line, answered with "OK ..." or "ERR ...". See ../../README.md.
//
// Needs the "Adafruit NeoPixel" library and the Seeed nRF52 board package (use the D6 macro, not a bare 6).
// The saved-settings feature uses InternalFileSystem from the same core; set DNA_USE_FS to 0 to build without it.
//
// LED power comes only from USB (VUSB). On battery alone the LEDs are unpowered, so the data pin must
// stay high-impedance (R1 only limits the current into the unpowered DIN protection diode).
// NOT compiled or flashed in the session that wrote it: build it once and check the points in README.md.
//
// Bring-up order (review item 06): 1) the start-up walk proves all 24 stages at low brightness,
// 2) check current and the farthest LED's VDD before raising MAX_BRIGHTNESS above ~25 % of 255
//    (full white is about 0.37 A @ 5 V; USB power only).
#include <Adafruit_NeoPixel.h>
#include <nrf.h>
#include <ctype.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#define DNA_USE_FS 1             // 1: SAVE/LOAD in internal flash, 0: disable
#if DNA_USE_FS
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
using namespace Adafruit_LittleFS_Namespace;
#endif

#define LED_PIN D6
#define N_LEDS 24
#define N_PAIRS 12
#define MAX_FRAMES 16
#define BRIGHTNESS 40            // 0..255, start-up value; the console may raise it up to MAX_BRIGHTNESS
#define MAX_BRIGHTNESS 128       // hard cap applied here, whatever the console asks for
#define DNA_LINE_MAX 192             // longest line: "F 15 " + 144 hex digits
#define CFG_PATH "/dna.cfg"
#define FRAME_MS 20              // render period

Adafruit_NeoPixel strip(N_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);  // GRB order, 800 kHz (datasheet p.7 / p.11)

// ---- state set by the console ------------------------------------------------------------------
static uint8_t frames[MAX_FRAMES][N_LEDS][3];   // RGB, full scale; brightness is applied at output
static uint8_t nFrames = 1;
static uint16_t holdMs = 1500;                  // time per frame when nFrames > 1
static uint8_t brightness = BRIGHTNESS;
static uint8_t fx = 1;                          // 0 static, 1 grow, 2 breathe, 3 wave, 4 codon scan
static uint8_t speedSel = 5;                    // 1 (slow) .. 10 (fast)

static bool usbPowered() {
  return (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk) != 0;
}

// ---- defaults: 5'-ATG GCA TCG TAA-3' as drawn on the silkscreen; strand B is the complement ----
static const char DEFAULT_SEQ[] = "ATGGCATCGTAA";

static void baseRgb(char b, uint8_t* rgb) {      // same colours as the earlier dna_led.ino at full scale
  rgb[0] = rgb[1] = rgb[2] = 0;
  switch (b) {
    case 'A': rgb[1] = 255; break;               // green
    case 'T': rgb[0] = 255; break;               // red
    case 'G': rgb[2] = 255; break;               // blue
    default:  rgb[0] = 255; rgb[1] = 128; break; // C: amber
  }
}

static char complement(char b) {
  return b == 'A' ? 'T' : b == 'T' ? 'A' : b == 'G' ? 'C' : 'G';
}

static void setDefaults() {
  memset(frames, 0, sizeof(frames));
  for (int k = 0; k < N_PAIRS; k++) {
    baseRgb(DEFAULT_SEQ[k], frames[0][2 * k]);
    baseRgb(complement(DEFAULT_SEQ[k]), frames[0][2 * k + 1]);
  }
  nFrames = 1;
  holdMs = 1500;
  brightness = BRIGHTNESS;
  fx = 1;
  speedSel = 5;
}

// ---- rendering ---------------------------------------------------------------------------------
static uint8_t outBuf[N_LEDS][3];
static bool outValid = false;

static void render(uint32_t now) {
  uint8_t fi = (nFrames > 1) ? (uint8_t)((now / holdMs) % nFrames) : 0;
  uint32_t stepMs = 60 + (10 - speedSel) * 60;   // 60 ms (fast) .. 600 ms (slow)
  uint8_t scale[N_LEDS];
  memset(scale, 255, sizeof(scale));

  switch (fx) {
    case 1: {                                    // grow: 0..12 pairs lit, then hold the full set
      uint8_t lit = (uint8_t)((now / stepMs) % 16);
      if (lit > N_PAIRS) lit = N_PAIRS;
      for (int k = lit; k < N_PAIRS; k++) scale[2 * k] = scale[2 * k + 1] = 0;
      break;
    }
    case 2: {                                    // breathe
      uint32_t period = stepMs * 16;
      float v = 0.5f - 0.5f * cosf(2.0f * PI * (float)(now % period) / (float)period);
      uint8_t s = (uint8_t)(20 + v * 235);
      memset(scale, s, sizeof(scale));
      break;
    }
    case 3: {                                    // wave travelling down the helix
      uint32_t period = stepMs * 24;
      float ph = (float)(now % period) / (float)period;
      for (int k = 0; k < N_PAIRS; k++) {
        float v = 0.5f + 0.5f * sinf(2.0f * PI * (ph - (float)k / N_PAIRS));
        scale[2 * k] = scale[2 * k + 1] = (uint8_t)(25 + v * 230);
      }
      break;
    }
    case 4: {                                    // one codon bright, the rest dim
      uint8_t c = (uint8_t)((now / (stepMs * 6)) % 4);
      for (int i = 0; i < N_LEDS; i++) scale[i] = (i / 6 == c) ? 255 : 30;
      break;
    }
    default: break;
  }

  bool changed = !outValid;
  for (int i = 0; i < N_LEDS; i++) {
    uint32_t s = (uint32_t)scale[i] * brightness / 255;      // 0..255
    for (int c = 0; c < 3; c++) {
      uint8_t v = (uint8_t)((uint32_t)frames[fi][i][c] * s / 255);
      if (v != outBuf[i][c]) { outBuf[i][c] = v; changed = true; }
    }
  }
  if (changed) {
    for (int i = 0; i < N_LEDS; i++) strip.setPixelColor(i, outBuf[i][0], outBuf[i][1], outBuf[i][2]);
    strip.show();
    outValid = true;
  }
}

static void walkTest() {                         // one pixel at a time: every one of the 24 stages must light in order
  for (int i = 0; i < N_LEDS; i++) {
    strip.clear();
    strip.setPixelColor(i, 10, 10, 10);
    strip.show();
    delay(60);
  }
  strip.clear();
  strip.show();
  outValid = false;                              // force the next render to redraw
}

// ---- command parser ----------------------------------------------------------------------------
static char* nextTok(char*& p) {
  while (*p == ' ') p++;
  if (!*p) return nullptr;
  char* s = p;
  while (*p && *p != ' ') p++;
  if (*p) *p++ = 0;
  return s;
}

static bool parseInt(const char* s, long lo, long hi, long& out) {
  if (!s || !*s) return false;
  char* end;
  long v = strtol(s, &end, 10);
  if (*end || v < lo || v > hi) return false;
  out = v;
  return true;
}

static int hexVal(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

static void say(bool loud, const char* s) { if (loud) Serial.println(s); }

static void dumpTo(Print& out) {                 // same text the console sends, so it doubles as the save format
  out.print("N ");  out.println(nFrames);
  out.print("T ");  out.println(holdMs);
  out.print("B ");  out.println(brightness);
  out.print("FX "); out.println(fx);
  out.print("SP "); out.println(speedSel);
  static const char HEX_DIGITS[] = "0123456789ABCDEF";
  for (int f = 0; f < nFrames; f++) {
    out.print("F "); out.print(f); out.print(' ');
    for (int i = 0; i < N_LEDS; i++)
      for (int c = 0; c < 3; c++) {
        out.print(HEX_DIGITS[frames[f][i][c] >> 4]);
        out.print(HEX_DIGITS[frames[f][i][c] & 15]);
      }
    out.println();
  }
}

#if DNA_USE_FS
static bool saveConfig() {
  InternalFS.remove(CFG_PATH);
  File f(InternalFS);
  if (!f.open(CFG_PATH, FILE_O_WRITE)) return false;
  dumpTo(f);
  f.close();
  return true;
}
#endif

static void execLine(char* line, bool loud);

#if DNA_USE_FS
static bool loadConfig() {
  File f(InternalFS);
  if (!f.open(CFG_PATH, FILE_O_READ)) return false;
  char buf[DNA_LINE_MAX];
  size_t n = 0;
  while (f.available()) {
    int c = f.read();
    if (c < 0) break;
    if (c == '\n') {
      buf[n] = 0;
      if (n) execLine(buf, false);
      n = 0;
    } else if (c != '\r' && n < DNA_LINE_MAX - 1) {
      buf[n++] = (char)c;
    }
  }
  f.close();
  return true;
}
#endif

static void execLine(char* line, bool loud) {
  char* p = line;
  char* cmd = nextTok(p);
  if (!cmd) return;
  for (char* c = cmd; *c; c++) *c = toupper(*c);
  long v;

  if (!strcmp(cmd, "HELLO")) {
    if (loud) {
      Serial.print("OK DNA-LED 1 leds=" ); Serial.print(N_LEDS);
      Serial.print(" frames=");            Serial.print(MAX_FRAMES);
      Serial.print(" maxbri=");            Serial.print(MAX_BRIGHTNESS);
      Serial.print(" fs=");                Serial.println(DNA_USE_FS);
    }
  } else if (!strcmp(cmd, "F")) {
    char* idx = nextTok(p);
    char* hex = nextTok(p);
    if (!parseInt(idx, 0, MAX_FRAMES - 1, v) || !hex || strlen(hex) != N_LEDS * 6) { say(loud, "ERR F <0-15> <144 hex>"); return; }
    uint8_t tmp[N_LEDS][3];
    for (int i = 0; i < N_LEDS * 3; i++) {
      int hi = hexVal(hex[2 * i]), lo = hexVal(hex[2 * i + 1]);
      if (hi < 0 || lo < 0) { say(loud, "ERR hex"); return; }
      tmp[i / 3][i % 3] = (uint8_t)(hi * 16 + lo);
    }
    memcpy(frames[v], tmp, sizeof(tmp));
    outValid = false;
    say(loud, "OK");
  } else if (!strcmp(cmd, "N")) {
    if (!parseInt(nextTok(p), 1, MAX_FRAMES, v)) { say(loud, "ERR N <1-16>"); return; }
    nFrames = (uint8_t)v;
    say(loud, "OK");
  } else if (!strcmp(cmd, "T")) {
    if (!parseInt(nextTok(p), 100, 60000, v)) { say(loud, "ERR T <100-60000>"); return; }
    holdMs = (uint16_t)v;
    say(loud, "OK");
  } else if (!strcmp(cmd, "B")) {
    if (!parseInt(nextTok(p), 0, 255, v)) { say(loud, "ERR B <0-255>"); return; }
    brightness = (uint8_t)(v > MAX_BRIGHTNESS ? MAX_BRIGHTNESS : v);
    if (loud) { Serial.print("OK "); Serial.println(brightness); }
  } else if (!strcmp(cmd, "FX")) {
    if (!parseInt(nextTok(p), 0, 4, v)) { say(loud, "ERR FX <0-4>"); return; }
    fx = (uint8_t)v;
    say(loud, "OK");
  } else if (!strcmp(cmd, "SP")) {
    if (!parseInt(nextTok(p), 1, 10, v)) { say(loud, "ERR SP <1-10>"); return; }
    speedSel = (uint8_t)v;
    say(loud, "OK");
  } else if (!strcmp(cmd, "DUMP")) {
    if (loud) { dumpTo(Serial); Serial.println("END"); }
  } else if (!strcmp(cmd, "CLR")) {
    memset(frames, 0, sizeof(frames));
    nFrames = 1;
    outValid = false;
    say(loud, "OK");
  } else if (!strcmp(cmd, "DEF")) {
    setDefaults();
    outValid = false;
    say(loud, "OK");
  } else if (!strcmp(cmd, "TEST")) {
    walkTest();
    say(loud, "OK");
  } else if (!strcmp(cmd, "SAVE")) {
#if DNA_USE_FS
    say(loud, saveConfig() ? "OK saved" : "ERR save failed");
#else
    say(loud, "ERR no fs");
#endif
  } else if (!strcmp(cmd, "LOAD")) {
#if DNA_USE_FS
    say(loud, loadConfig() ? "OK loaded" : "ERR no saved settings");
    outValid = false;
#else
    say(loud, "ERR no fs");
#endif
  } else {
    say(loud, "ERR unknown command");
  }
}

// ---- serial input: non-blocking line reader ----------------------------------------------------
static char rxBuf[DNA_LINE_MAX];
static size_t rxLen = 0;
static bool rxOverflow = false;

static void pollSerial() {
  while (Serial.available()) {
    int c = Serial.read();
    if (c < 0) break;
    if (c == '\n') {
      if (rxOverflow) {
        Serial.println("ERR line too long");
      } else {
        rxBuf[rxLen] = 0;
        if (rxLen) execLine(rxBuf, true);
      }
      rxLen = 0;
      rxOverflow = false;
    } else if (c != '\r') {
      if (rxLen < DNA_LINE_MAX - 1) rxBuf[rxLen++] = (char)c;
      else rxOverflow = true;
    }
  }
}

// ---- Arduino entry points ----------------------------------------------------------------------
void setup() {
  Serial.begin(115200);        // never wait for a host: the board must also run standalone on a charger
  while (!usbPowered()) {      // battery only: leave D6 floating until USB 5 V is present
    pinMode(LED_PIN, INPUT);
    delay(200);
  }
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  delay(100);                  // let the LED supply settle before any data is sent
  strip.begin();
  strip.clear();
  strip.show();

  setDefaults();
#if DNA_USE_FS
  InternalFS.begin();
  loadConfig();                // keeps the defaults when nothing was saved
#endif
  walkTest();                  // bring-up: all 24 stages in order, at low brightness
}

void loop() {
  if (!usbPowered()) {         // USB removed: stop driving the data line
    pinMode(LED_PIN, INPUT);
    delay(200);
    NVIC_SystemReset();        // restart cleanly when USB returns
  }
  pollSerial();
  static uint32_t last = 0;
  uint32_t now = millis();
  if (now - last >= FRAME_MS) {
    last = now;
    render(now);
  }
}
