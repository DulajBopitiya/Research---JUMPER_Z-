#pragma once
#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

class LedMatrix
{
public:
    // Small RGB helper used by JsonBridge / mapping helpers
    typedef struct RGB
    {
        uint8_t r, g, b;
    }RGB_t;

    // ===================== CONSTANTS =====================
    static constexpr uint16_t NUM_LEDS = 400;
    static constexpr uint32_t BLINK_PERIOD_MS = 350;

    // ===================== LED STRIP CONTROL =====================
    // Call once in setup()
    static void begin(uint8_t brightness = 20);

    // Access the underlying strip (for JsonBridge etc.)
    static Adafruit_NeoPixel &strip();

    static void setBrightness(uint8_t brightness);
    static void clear();
    static void show();

    // Safe pixel setter (index bounds checked)
    static void setPixelRGB(int idx, uint8_t r, uint8_t g, uint8_t b);

    // ===================== TOP POWER RAILS =====================
    static constexpr uint16_t TOP_BASE = 0;
    static constexpr uint8_t TOP_ROWS = 2;
    static constexpr uint8_t TOP_COLS = 25;
    static constexpr uint8_t TOP_BLOCK_WIDTH = 5;
    static constexpr uint16_t TOP_COUNT = 50;

    static uint16_t topRailIndex(uint8_t row, uint8_t col);

    // ===================== MIDDLE SECTION 1 =====================
    static constexpr uint16_t MID1_BASE = 50;
    static constexpr uint8_t MID1_ROWS = 5;
    static constexpr uint8_t MID1_COLS = 30;
    static constexpr uint16_t MID1_COUNT = 150;

    static uint16_t mid1Index(uint8_t row, uint8_t col);

    // ===================== MIDDLE SECTION 2 =====================
    static constexpr uint16_t MID2_BASE = 200;
    static constexpr uint8_t MID2_ROWS = 5;
    static constexpr uint8_t MID2_COLS = 30;
    static constexpr uint16_t MID2_COUNT = 150;

    static uint16_t mid2Index(uint8_t row, uint8_t col);

    // ===================== BOTTOM SECTION =====================
    static constexpr uint16_t BOTTOM_BASE = 350;
    static constexpr uint8_t BOTTOM_ROWS = 2;
    static constexpr uint8_t BOTTOM_COLS = 25;
    static constexpr uint8_t BOTTOM_BLOCK_WIDTH = 5;
    static constexpr uint16_t BOTTOM_COUNT = 50;

    static uint16_t bottomRailIndex(uint8_t row, uint8_t col);

    // ===================== VALIDATORS =====================
    static bool isValidTop(uint8_t row, uint8_t col);
    static bool isValidBottom(uint8_t row, uint8_t col);
    static bool isValidMid1(uint8_t row, uint8_t col);
    static bool isValidMid2(uint8_t row, uint8_t col);

    // ===================== LOGICAL -> LED INDEX HELPERS =====================
    // "T"  : top rails (2x25)
    // "B"  : bottom rails (2x25)
    // "M1" : middle section 1 (5x30)
    // "M2" : middle section 2 (5x30)
    // Returns -1 on invalid.
    static int logicalToIndex(const char *sec, int row, int col);

    // Wokwi-ish colors: names like "red"/"green"... or "#RRGGBB".
    // Unknown -> white.
    static RGB wokwiColorToRgb(const char *name);

    // ===================== WIRE FRAMEBUFFER (ENDPOINT BLINK) =====================
    static void frameClear();
    static void frameResetBlink();
    static void framePaintPathIdx(int idx, const RGB &c);
    static void frameMarkEndpointIdx(int idx, const RGB &c);
    static void frameApplyFull();
    static void frameTick();

    // Scale every pixel in the framebuffer by factor/255.
    // factor=64 → ~25% brightness. Leaves endpoint blink markers intact.
    static void frameDimAll(uint8_t factor);

    // Apply the framebuffer to the NeoPixel hardware buffer WITHOUT calling
    // show().  Use this when you need to overlay additional pixels (e.g.
    // CurrentViz sparks) before a single show() call.
    // frameApplyFull() is equivalent to frameApplyToBuffer() + show().
    static void frameApplyToBuffer();

    // Snapshot — save the full-brightness frame before a measurement dims it,
    // so it can be restored exactly (used by measure / measure_clear).
    static void frameSaveSnapshot();
    static void frameRestoreSnapshot();
    static bool frameHasSnapshot();
    static void frameClearSnapshot();   // discard saved snapshot

    // Returns true if the given strip index has any non-zero colour in the
    // framebuffer (path or endpoint).  Used by CurrentViz to restrict the
    // animated comet to pixels that paintBridgeLeds actually painted.
    static bool frameIsLit(int idx);

    // Dump framebuffer to stream for debug.
    // Outputs:
    //   LED_DUMP_BEGIN\n
    //   PATH:<2400 hex chars>\n   (path RGB for all 400 LEDs)
    //   ENDP:<2400 hex chars>\n   (endpoint RGB for all 400 LEDs)
    //   EP:<400 chars>\n          ('1' if endpoint, '0' otherwise)
    //   LED_DUMP_END\n
    static void frameDump(Stream &out);

private:
    // IMPORTANT: defined ONLY ONCE in Led_Matrix.cpp
    static Adafruit_NeoPixel s_strip;
};