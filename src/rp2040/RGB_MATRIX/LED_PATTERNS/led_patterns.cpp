#include "led_patterns.h"
#include "../Led_Matrix.h"

namespace rgbPatterns {

// ── Rainbow wheel ──────────────────────────────────────────────────────────
static uint32_t hueWheel(Adafruit_NeoPixel &strip, uint8_t pos) {
    if (pos < 85)  return strip.Color(pos * 3, 255 - pos * 3, 0);
    if (pos < 170) { pos -= 85;  return strip.Color(255 - pos * 3, 0, pos * 3); }
    pos -= 170;    return strip.Color(0, pos * 3, 255 - pos * 3);
}

// ── 5-row × 3-col pixel font ───────────────────────────────────────────────
// Each uint8_t encodes one row: bit2 = left col, bit1 = centre col, bit0 = right col
static const uint8_t FONT_F[5]     = { 0b111, 0b100, 0b110, 0b100, 0b100 };
static const uint8_t FONT_A[5]     = { 0b010, 0b101, 0b111, 0b101, 0b101 };
static const uint8_t FONT_B[5]     = { 0b110, 0b101, 0b110, 0b101, 0b110 };
static const uint8_t FONT_V[5]     = { 0b101, 0b101, 0b101, 0b101, 0b010 };
static const uint8_t FONT_O[5]     = { 0b010, 0b101, 0b101, 0b101, 0b010 };
static const uint8_t FONT_L[5]     = { 0b100, 0b100, 0b100, 0b100, 0b111 };
static const uint8_t FONT_T[5]     = { 0b111, 0b010, 0b010, 0b010, 0b010 };
static const uint8_t FONT_P[5]     = { 0b110, 0b101, 0b110, 0b100, 0b100 };
static const uint8_t FONT_R[5]     = { 0b110, 0b101, 0b110, 0b110, 0b101 };
static const uint8_t FONT_M[5]     = { 0b101, 0b111, 0b101, 0b101, 0b101 };
static const uint8_t FONT_I[5]     = { 0b111, 0b010, 0b010, 0b010, 0b111 };
static const uint8_t FONT_X[5]     = { 0b101, 0b101, 0b010, 0b101, 0b101 };
static const uint8_t FONT_1[5]     = { 0b010, 0b110, 0b010, 0b010, 0b111 };
static const uint8_t FONT_SPACE[5] = { 0b000, 0b000, 0b000, 0b000, 0b000 };

// Legacy glyphs kept for showName()
static const uint8_t FONT_J[5]     = { 0b011, 0b001, 0b001, 0b101, 0b010 };
static const uint8_t FONT_U[5]     = { 0b101, 0b101, 0b101, 0b101, 0b111 };
static const uint8_t FONT_E[5]     = { 0b111, 0b100, 0b110, 0b100, 0b111 };
static const uint8_t FONT_HYPHEN[5]= { 0b000, 0b000, 0b111, 0b000, 0b000 };
static const uint8_t FONT_Z[5]     = { 0b111, 0b001, 0b010, 0b100, 0b111 };

// ── Low-level helpers ──────────────────────────────────────────────────────

// Render one character; startCol may be negative or beyond 29 (clipped).
static void renderChar(Adafruit_NeoPixel &strip,
                       const uint8_t *glyph, bool mid2,
                       int startCol, uint8_t r, uint8_t g, uint8_t b) {
    for (int row = 0; row < 5; row++) {
        for (int bit = 0; bit < 3; bit++) {
            if (!(glyph[row] & (0x04 >> bit))) continue;
            int col = startCol + bit;
            if (col < 0 || col >= 30) continue;
            uint16_t idx = mid2
                ? LedMatrix::mid2Index((uint8_t)row, (uint8_t)col)
                : LedMatrix::mid1Index((uint8_t)row, (uint8_t)col);
            if (idx == 0xFFFF) continue;
            strip.setPixelColor(idx, r, g, b);
        }
    }
}

// Blank every LED in a 5×30 mid section.
static void clearSection(Adafruit_NeoPixel &strip, bool mid2) {
    for (int col = 0; col < 30; col++)
        for (int row = 0; row < 5; row++)
            strip.setPixelColor(mid2 ? LedMatrix::mid2Index((uint8_t)row, (uint8_t)col)
                                     : LedMatrix::mid1Index((uint8_t)row, (uint8_t)col),
                                0, 0, 0);
}

// Smooth breathing brightness.  phase 0-255 → bri 20-255.
// Uses a squared triangle wave so the glow lingers at the bright/dim extremes
// and transitions quickly through the middle — feels like natural breathing.
static uint8_t breathBri(uint8_t phase) {
    uint16_t tri = (phase < 128) ? (uint16_t)phase * 2
                                 : (uint16_t)(255 - phase) * 2;
    uint16_t sq  = (tri * tri) >> 8;              // 0-255
    return (uint8_t)(20 + (uint16_t)sq * 235 / 255);
}

// "FABVOLT" — 7 chars × (3 wide + 1 gap) = 28 cols, anchored at col 1.
static const uint8_t *kFabvolt[7] = {
    FONT_F, FONT_A, FONT_B, FONT_V, FONT_O, FONT_L, FONT_T
};

// Draw all FABVOLT letters on M1 in gold scaled to bri.
static void drawFabvolt(Adafruit_NeoPixel &strip, uint8_t bri) {
    uint8_t r = bri;
    uint8_t g = (uint8_t)((uint16_t)bri * 165 / 255);
    for (int i = 0; i < 7; i++)
        renderChar(strip, kFabvolt[i], false, 1 + i * 4, r, g, 0);
}

// ── showName (legacy public API — kept for compatibility) ──────────────────
void showName(Adafruit_NeoPixel &strip) {
    strip.clear();
    const int START_COL = 7;
    const int CHAR_STEP = 4;
    struct CharDef { const uint8_t *glyph; bool mid2; };
    const CharDef chars[8] = {
        { FONT_J, false }, { FONT_U, false }, { FONT_M, false }, { FONT_P, false },
        { FONT_E, true  }, { FONT_R, true  }, { FONT_HYPHEN, true }, { FONT_Z, true },
    };
    for (int i = 0; i < 8; i++) {
        uint32_t c = hueWheel(strip, (uint8_t)(i * 32));
        renderChar(strip, chars[i].glyph, chars[i].mid2,
                   START_COL + (i % 4) * CHAR_STEP,
                   (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF);
    }
    strip.show();
}

// ── startup — FabVolt ProtoMatrix V1 boot animation ───────────────────────
void startup(Adafruit_NeoPixel &strip) {
    const int N = LedMatrix::NUM_LEDS;   // 400

    // ── Phase 1 ── Rainbow comet sweeps across all 400 LEDs (~840 ms) ──────
    {
        const int TAIL = 20;
        for (int head = 0; head < N + TAIL; head++) {
            strip.clear();
            for (int t = 0; t < TAIL; t++) {
                int idx = head - t;
                if (idx < 0 || idx >= N) continue;
                uint8_t  bri = (uint8_t)(255 - t * 255 / TAIL);
                uint32_t c   = hueWheel(strip, (uint8_t)(idx * 255 / N));
                strip.setPixelColor(idx,
                    (uint8_t)(((c >> 16) & 0xFF) * bri / 255),
                    (uint8_t)(((c >>  8) & 0xFF) * bri / 255),
                    (uint8_t)(( c        & 0xFF) * bri / 255));
            }
            strip.show();
            delay(2);
        }
    }

    // ── Phase 2 ── "FABVOLT" flashes in on M1, letter by letter (~1.1 s) ──
    // Each letter: 50 ms white flash → 110 ms settle to gold (×7 = 1120 ms + 300 ms hold)
    {
        strip.clear();
        strip.show();
        for (int ch = 0; ch < 7; ch++) {
            // Bright white-warm flash to catch the eye
            renderChar(strip, kFabvolt[ch], false, 1 + ch * 4, 255, 255, 210);
            strip.show();
            delay(50);
            // Settle to gold
            renderChar(strip, kFabvolt[ch], false, 1 + ch * 4, 255, 165, 0);
            strip.show();
            delay(110);
        }
        delay(300);   // brief hold: all seven letters glowing gold
    }

    // ── Phase 3+4 ── FABVOLT breathes on M1; "PROTOMATRIX V1" scrolls on M2 ──
    //
    // Breathing:  phase += 3 per frame at 15 ms → full cycle ≈ 1280 ms
    //             starts at phase 128 (peak brightness) for a smooth handoff
    // Scroll:     begins after 1500 ms of breathing
    //             14 chars × 4 cols = 56 px wide; starts off-screen right (x = 30),
    //             counts down until the last char exits left (x = -56)
    //             → 86 frames × 15 ms ≈ 1290 ms for the full ticker pass
    {
        static const uint8_t *kScroll[] = {
            FONT_P, FONT_R, FONT_O, FONT_T, FONT_O, FONT_M, FONT_A, FONT_T,
            FONT_R, FONT_I, FONT_X, FONT_SPACE, FONT_V, FONT_1
        };
        const int SCROLL_LEN  = 14;
        const int SCROLL_STEP = 4;    // 3-px glyph + 1-px gap

        uint8_t  breathPhase = 128;   // start at brightness peak
        int      scrollOff   = 30;    // leftmost x of text string (off-screen right)
        bool     scrolling   = false;
        uint32_t tStart      = millis();

        while (scrollOff > -(SCROLL_LEN * SCROLL_STEP)) {
            // ── M1: breathing FABVOLT ──
            breathPhase += 3;
            clearSection(strip, false);
            drawFabvolt(strip, breathBri(breathPhase));

            // ── M2: scrolling ticker (kicks in after 1500 ms) ──
            if (!scrolling && (millis() - tStart) >= 1500)
                scrolling = true;

            if (scrolling) {
                clearSection(strip, true);
                // Ice-blue: RGB(0, 190, 255)
                for (int i = 0; i < SCROLL_LEN; i++)
                    renderChar(strip, kScroll[i], true,
                               scrollOff + i * SCROLL_STEP, 0, 190, 255);
                scrollOff--;
            }

            strip.show();
            delay(25);
        }

        // ── Combined hold: FABVOLT at peak brightness, M2 clear ──
        clearSection(strip, true);
        clearSection(strip, false);
        drawFabvolt(strip, 255);
        strip.show();
        delay(500);
    }

    // ── Phase 5 ── Gold + ice-blue sparkle fade across all LEDs (~1.5 s) ──
    {
        const uint32_t DURATION_MS = 1500;
        const int      SPAWN_RATE  = 10;
        const uint8_t  DECAY       = 16;
        const int      FRAME_MS    = 20;

        uint8_t bri[LedMatrix::NUM_LEDS];
        uint8_t col[LedMatrix::NUM_LEDS];
        memset(bri, 0, sizeof(bri));
        memset(col, 0, sizeof(col));

        uint32_t tStart = millis();
        while (millis() - tStart < DURATION_MS) {
            for (int s = 0; s < SPAWN_RATE; s++) {
                int idx = (int)random(N);
                if (bri[idx] == 0) {
                    bri[idx] = (uint8_t)(120 + random(136));
                    col[idx] = (uint8_t)random(3);
                }
            }
            for (int i = 0; i < N; i++) {
                uint8_t v = bri[i];
                if (v == 0) { strip.setPixelColor(i, 0, 0, 0); continue; }
                uint8_t r, g, b;
                switch (col[i]) {
                    case 0:  r = v; g = (uint8_t)((uint16_t)v*165/255); b = 0; break; // gold
                    case 1:  r = 0; g = (uint8_t)((uint16_t)v*190/255); b = v; break; // ice-blue
                    default: r = v; g = v;                               b = v; break; // white
                }
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

}  // namespace rgbPatterns
