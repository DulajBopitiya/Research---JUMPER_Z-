#include "led_patterns.h"
#include "../Led_Matrix.h"

namespace rgbPatterns {

    // Rainbow color wheel: 0-255 maps full hue cycle
    static uint32_t hueWheel(Adafruit_NeoPixel &strip, uint8_t pos) {
        if (pos < 85)  return strip.Color(pos * 3, 255 - pos * 3, 0);
        if (pos < 170) { pos -= 85;  return strip.Color(255 - pos * 3, 0, pos * 3); }
        pos -= 170;    return strip.Color(0, pos * 3, 255 - pos * 3);
    }

    void startup(Adafruit_NeoPixel &strip) {
        const int N = LedMatrix::NUM_LEDS;  // 400

        // Phase 1: Rainbow comet sweeps across all 400 LEDs
        // A bright head drags a fading rainbow tail behind it.
        const int TAIL = 20;
        for (int head = 0; head < N + TAIL; head++) {
            strip.clear();
            for (int t = 0; t < TAIL; t++) {
                int idx = head - t;
                if (idx < 0 || idx >= N) continue;
                uint8_t bri = (uint8_t)(255 - t * 255 / TAIL);
                uint32_t c  = hueWheel(strip, (uint8_t)(idx * 255 / N));
                uint8_t r   = ((c >> 16) & 0xFF) * bri / 255;
                uint8_t g   = ((c >> 8)  & 0xFF) * bri / 255;
                uint8_t b   = ( c        & 0xFF) * bri / 255;
                strip.setPixelColor(idx, r, g, b);
            }
            strip.show();
            delay(2);   // full sweep ~840 ms
        }

        // Phase 2: Sections light up one-by-one with distinct colors
        // Top rails (0-49): cyan
        for (int i = 0; i < 50; i++)    strip.setPixelColor(i, 0, 210, 210);
        strip.show(); delay(90);

        // Mid section 1 (50-199): electric blue
        for (int i = 50; i < 200; i++)  strip.setPixelColor(i, 0, 80, 255);
        strip.show(); delay(90);

        // Mid section 2 (200-349): violet
        for (int i = 200; i < 350; i++) strip.setPixelColor(i, 130, 0, 255);
        strip.show(); delay(90);

        // Bottom rails (350-399): magenta
        for (int i = 350; i < N; i++)   strip.setPixelColor(i, 210, 0, 180);
        strip.show(); delay(180);

        // Phase 3: Full white flash
        for (int i = 0; i < N; i++) strip.setPixelColor(i, 255, 255, 255);
        strip.show(); delay(80);

        // Phase 4: Smooth fade to black
        for (int v = 255; v >= 0; v -= 5) {
            uint8_t bv = (uint8_t)v;
            for (int i = 0; i < N; i++) strip.setPixelColor(i, bv, bv, bv);
            strip.show();
            delay(8);
        }
        strip.clear();
        strip.show();
    }
}
