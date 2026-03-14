#include "led_patterns.h"
#include "../Led_Matrix.h"

namespace rgbPatterns {

    // Rainbow color wheel: 0-255 maps full hue cycle
    static uint32_t hueWheel(Adafruit_NeoPixel &strip, uint8_t pos) {
        if (pos < 85)  return strip.Color(pos * 3, 255 - pos * 3, 0);
        if (pos < 170) { pos -= 85;  return strip.Color(255 - pos * 3, 0, pos * 3); }
        pos -= 170;    return strip.Color(0, pos * 3, 255 - pos * 3);
    }

    // ── 5-row x 3-col pixel font ─────────────────────────────────────────────
    // Each uint8_t = one row: bit2 = left col, bit1 = center col, bit0 = right col
    //
    //  bit2 bit1 bit0
    //   L    C    R
    //
    static const uint8_t FONT_J[5] = { 0b011, 0b001, 0b001, 0b101, 0b010 };
    //  . # #
    //  . . #
    //  . . #
    //  # . #
    //  . # .

    static const uint8_t FONT_U[5] = { 0b101, 0b101, 0b101, 0b101, 0b111 };
    //  # . #
    //  # . #
    //  # . #
    //  # . #
    //  # # #

    static const uint8_t FONT_M[5] = { 0b101, 0b111, 0b101, 0b101, 0b101 };
    //  # . #
    //  # # #
    //  # . #
    //  # . #
    //  # . #

    static const uint8_t FONT_P[5] = { 0b110, 0b101, 0b110, 0b100, 0b100 };
    //  # # .
    //  # . #
    //  # # .
    //  # . .
    //  # . .

    static const uint8_t FONT_E[5] = { 0b111, 0b100, 0b110, 0b100, 0b111 };
    //  # # #
    //  # . .
    //  # # .
    //  # . .
    //  # # #

    static const uint8_t FONT_R[5] = { 0b110, 0b101, 0b110, 0b110, 0b101 };
    //  # # .
    //  # . #
    //  # # .
    //  # # .
    //  # . #

    static const uint8_t FONT_HYPHEN[5] = { 0b000, 0b000, 0b111, 0b000, 0b000 };
    //  . . .
    //  . . .
    //  # # #
    //  . . .
    //  . . .

    static const uint8_t FONT_Z[5] = { 0b111, 0b001, 0b010, 0b100, 0b111 };
    //  # # #
    //  . . #
    //  . # .
    //  # . .
    //  # # #

    // ── Render one character onto M1 or M2 ───────────────────────────────────
    // startCol: left edge column (0-29 within section)
    // useMid2:  false = M1 section, true = M2 section
    static void renderChar(Adafruit_NeoPixel &strip,
                           const uint8_t *glyph, bool useMid2,
                           int startCol, uint8_t r, uint8_t g, uint8_t b) {
        for (int row = 0; row < 5; row++) {
            for (int bit = 0; bit < 3; bit++) {
                if (!(glyph[row] & (0x04 >> bit))) continue;  // 0x04 = bit2
                int col = startCol + bit;
                if (col < 0 || col >= 30) continue;
                uint16_t idx = useMid2
                    ? LedMatrix::mid2Index((uint8_t)row, (uint8_t)col)
                    : LedMatrix::mid1Index((uint8_t)row, (uint8_t)col);
                if (idx == 0xFFFF) continue;
                strip.setPixelColor(idx, r, g, b);
            }
        }
    }

    void showName(Adafruit_NeoPixel &strip) {
        strip.clear();

        // 4 chars per section, each 3-wide with 1-col gap = 15 cols total
        // Centered in 30 cols: left margin = (30 - 15) / 2 = 7
        const int START_COL = 7;
        const int CHAR_STEP = 4;  // 3 wide + 1 gap

        // "JUMP" on M1, "ER-Z" on M2
        // Each character gets a rainbow hue (8 chars, evenly spaced across the wheel)
        struct CharDef { const uint8_t *glyph; bool mid2; };
        const CharDef chars[8] = {
            { FONT_J,      false },
            { FONT_U,      false },
            { FONT_M,      false },
            { FONT_P,      false },
            { FONT_E,      true  },
            { FONT_R,      true  },
            { FONT_HYPHEN, true  },
            { FONT_Z,      true  },
        };

        for (int i = 0; i < 8; i++) {
            uint32_t c = hueWheel(strip, (uint8_t)(i * 32));  // 0,32,64...224
            uint8_t  r = (c >> 16) & 0xFF;
            uint8_t  g = (c >> 8)  & 0xFF;
            uint8_t  b =  c        & 0xFF;
            int col = START_COL + (i % 4) * CHAR_STEP;
            renderChar(strip, chars[i].glyph, chars[i].mid2, col, r, g, b);
        }

        strip.show();
    }

    void startup(Adafruit_NeoPixel &strip) {
        const int N = LedMatrix::NUM_LEDS;  // 400

        // Phase 1: Rainbow comet sweeps across all 400 LEDs
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

        // Phase 2: Show "JUMPER-Z" on M1 + M2, hold for 1.5 s
        showName(strip);
        delay(3000);

        // Phase 3: Twinkling white and warm-yellow sparkles across all 400 LEDs
        {
            const uint32_t DURATION_MS = 2500;
            const int      SPAWN_RATE  = 12;   // new sparkles spawned per frame
            const uint8_t  DECAY       = 15;   // brightness step-down per frame
            const int      FRAME_MS    = 20;

            // Per-LED state — block-scoped so stack is freed when done
            uint8_t bri[LedMatrix::NUM_LEDS];
            uint8_t col[LedMatrix::NUM_LEDS];  // 0=white  1=warm-yellow  2=warm-white
            memset(bri, 0, sizeof(bri));
            memset(col, 0, sizeof(col));

            uint32_t tStart = millis();
            while (millis() - tStart < DURATION_MS) {
                // Spawn new sparkles on currently dark LEDs
                for (int s = 0; s < SPAWN_RATE; s++) {
                    int idx = (int)random(N);
                    if (bri[idx] == 0) {
                        bri[idx] = (uint8_t)(180 + random(76));  // 180–255
                        col[idx] = (uint8_t)random(3);
                    }
                }
                // Render each LED and decay its brightness
                for (int i = 0; i < N; i++) {
                    uint8_t v = bri[i];
                    if (v == 0) { strip.setPixelColor(i, 0, 0, 0); continue; }
                    uint8_t r, g, b;
                    if      (col[i] == 0) { r = v; g = v; b = v; }                              // pure white
                    else if (col[i] == 1) { r = v; g = (uint8_t)(v * 200 / 255); b = (uint8_t)(v * 50  / 255); }  // warm yellow
                    else                  { r = v; g = (uint8_t)(v * 230 / 255); b = (uint8_t)(v * 150 / 255); }  // warm white
                    strip.setPixelColor(i, r, g, b);
                    bri[i] = (v > DECAY) ? v - DECAY : 0;
                }
                strip.show();
                delay(FRAME_MS);
            }
            strip.clear();
            strip.show();
        }
    }

}
