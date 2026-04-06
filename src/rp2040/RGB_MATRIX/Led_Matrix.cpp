#include "Led_Matrix.h"
#include "configuration.h"   // RGB_LED_PIN, NEO_GRB, etc (from your project)

// ====== Internal wire-frame state (endpoints blink) ======
static uint8_t s_pathR[LedMatrix::NUM_LEDS];
static uint8_t s_pathG[LedMatrix::NUM_LEDS];
static uint8_t s_pathB[LedMatrix::NUM_LEDS];

static uint8_t s_endR[LedMatrix::NUM_LEDS];
static uint8_t s_endG[LedMatrix::NUM_LEDS];
static uint8_t s_endB[LedMatrix::NUM_LEDS];

static bool s_isEndpoint[LedMatrix::NUM_LEDS];
static bool s_haveFrame = false;

static bool s_blinkOn = true;
static uint32_t s_lastBlinkMs = 0;

// Snapshot buffers — saved before measurement dims the frame
static uint8_t s_snapPathR[LedMatrix::NUM_LEDS];
static uint8_t s_snapPathG[LedMatrix::NUM_LEDS];
static uint8_t s_snapPathB[LedMatrix::NUM_LEDS];
static uint8_t s_snapEndR[LedMatrix::NUM_LEDS];
static uint8_t s_snapEndG[LedMatrix::NUM_LEDS];
static uint8_t s_snapEndB[LedMatrix::NUM_LEDS];
static bool    s_snapIsEndpoint[LedMatrix::NUM_LEDS];
static bool    s_haveSnapshot = false;

// ---------------- helpers ----------------
static int hexNibble(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return 10 + (c - 'a');
    if (c >= 'A' && c <= 'F') return 10 + (c - 'A');
    return -1;
}

static bool parseHexColor(const char *s, LedMatrix::RGB &out)
{
    // "#RRGGBB"
    if (!s || s[0] != '#' || !s[1] || !s[2] || !s[3] || !s[4] || !s[5] || !s[6]) return false;

    int r1 = hexNibble(s[1]), r2 = hexNibble(s[2]);
    int g1 = hexNibble(s[3]), g2 = hexNibble(s[4]);
    int b1 = hexNibble(s[5]), b2 = hexNibble(s[6]);
    if (r1 < 0 || r2 < 0 || g1 < 0 || g2 < 0 || b1 < 0 || b2 < 0) return false;

    out.r = (uint8_t)((r1 << 4) | r2);
    out.g = (uint8_t)((g1 << 4) | g2);
    out.b = (uint8_t)((b1 << 4) | b2);
    return true;
}

static void applyEndpointsOnly()
{
    for (int i = 0; i < (int)LedMatrix::NUM_LEDS; i++)
    {
        if (!s_isEndpoint[i]) continue;

        if (s_blinkOn)
            LedMatrix::strip().setPixelColor((uint16_t)i, LedMatrix::strip().Color(s_endR[i], s_endG[i], s_endB[i]));
        else
            LedMatrix::strip().setPixelColor((uint16_t)i, LedMatrix::strip().Color(s_pathR[i], s_pathG[i], s_pathB[i]));
    }

    LedMatrix::strip().show();
}


// ===================== STRIP DEFINITION (ONLY HERE) =====================
// This MUST NOT be in the header, otherwise you get multiple definition errors.
Adafruit_NeoPixel LedMatrix::s_strip(LedMatrix::NUM_LEDS, RGB_LED_PIN, NEO_GRB + NEO_KHZ800);

// ===================== LED STRIP CONTROL =====================

void LedMatrix::begin(uint8_t brightness)
{
    s_strip.begin();
    s_strip.setBrightness(brightness);
    s_strip.show();
}

Adafruit_NeoPixel &LedMatrix::strip()
{
    return s_strip;
}

void LedMatrix::setBrightness(uint8_t brightness)
{
    s_strip.setBrightness(brightness);
}

void LedMatrix::clear()
{
    s_strip.clear();
}

void LedMatrix::show()
{
    s_strip.show();
}

void LedMatrix::setPixelRGB(int idx, uint8_t r, uint8_t g, uint8_t b)
{
    if (idx < 0 || idx >= (int)NUM_LEDS) return;
    s_strip.setPixelColor((uint16_t)idx, s_strip.Color(r, g, b));
}

// ===================== VALIDATORS =====================

bool LedMatrix::isValidTop(uint8_t row, uint8_t col)
{
    return (row < TOP_ROWS) && (col < TOP_COLS);
}

bool LedMatrix::isValidBottom(uint8_t row, uint8_t col)
{
    return (row < BOTTOM_ROWS) && (col < BOTTOM_COLS);
}

bool LedMatrix::isValidMid1(uint8_t row, uint8_t col)
{
    return (row < MID1_ROWS) && (col < MID1_COLS);
}

bool LedMatrix::isValidMid2(uint8_t row, uint8_t col)
{
    return (row < MID2_ROWS) && (col < MID2_COLS);
}

// ===================== INDEX MAPPERS =====================

uint16_t LedMatrix::topRailIndex(uint8_t row, uint8_t col)
{
    if (!isValidTop(row, col)) return 0xFFFF;

    const uint8_t block = col / TOP_BLOCK_WIDTH;
    const uint8_t localCol = col % TOP_BLOCK_WIDTH;
    const uint16_t blockBase = TOP_BASE + (uint16_t)block * 10;

    if (row == 0) return blockBase + localCol;
    return blockBase + (9 - localCol);
}

uint16_t LedMatrix::bottomRailIndex(uint8_t row, uint8_t col)
{
    if (!isValidBottom(row, col)) return 0xFFFF;

    const uint8_t block = col / BOTTOM_BLOCK_WIDTH;
    const uint8_t localCol = col % BOTTOM_BLOCK_WIDTH;
    const uint16_t blockBase = BOTTOM_BASE + (uint16_t)block * 10;

    if (row == 0) return blockBase + localCol;
    return blockBase + (9 - localCol);
}

uint16_t LedMatrix::mid1Index(uint8_t row, uint8_t col)
{
    if (!isValidMid1(row, col)) return 0xFFFF;
    return MID1_BASE + (uint16_t)col * MID1_ROWS + row;
}

uint16_t LedMatrix::mid2Index(uint8_t row, uint8_t col)
{
    if (!isValidMid2(row, col)) return 0xFFFF;
    return MID2_BASE + (uint16_t)col * MID2_ROWS + row;
}

// ===================== LOGICAL -> LED INDEX HELPERS =====================

int LedMatrix::logicalToIndex(const char *sec, int row, int col)
{
    if (!sec) return -1;

    uint16_t idx = 0xFFFF;

    if (!strcmp(sec, "T")) idx = LedMatrix::topRailIndex((uint8_t)row, (uint8_t)col);
    else if (!strcmp(sec, "B")) idx = LedMatrix::bottomRailIndex((uint8_t)row, (uint8_t)col);
    else if (!strcmp(sec, "M1")) idx = LedMatrix::mid1Index((uint8_t)row, (uint8_t)col);
    else if (!strcmp(sec, "M2")) idx = LedMatrix::mid2Index((uint8_t)row, (uint8_t)col);

    return (idx == 0xFFFF) ? -1 : (int)idx;
}

LedMatrix::RGB LedMatrix::wokwiColorToRgb(const char *name)
{
    RGB c{255, 255, 255}; // default white
    if (!name || name[0] == '\0') return c;

    if (name[0] == '#')
    {
        RGB hx;
        if (parseHexColor(name, hx)) return hx;
        return c;
    }

    if (!strcmp(name, "red")) return RGB{255, 0, 0};
    if (!strcmp(name, "green")) return RGB{0, 255, 0};
    if (!strcmp(name, "blue")) return RGB{0, 0, 255};
    if (!strcmp(name, "yellow")) return RGB{255, 255, 0};
    if (!strcmp(name, "orange")) return RGB{255, 128, 0};
    if (!strcmp(name, "purple")) return RGB{180, 0, 255};
    if (!strcmp(name, "pink")) return RGB{255, 0, 150};
    if (!strcmp(name, "cyan")) return RGB{0, 255, 255};
    if (!strcmp(name, "white")) return RGB{255, 255, 255};
    if (!strcmp(name, "black")) return RGB{10, 10, 10};   // visible “black”
    if (!strcmp(name, "gray")) return RGB{128, 128, 128};
    if (!strcmp(name, "grey")) return RGB{80, 80, 80};
    if (!strcmp(name, "brown")) return RGB{120, 60, 0};
    if (!strcmp(name, "magenta")) return RGB{255, 0, 255};

    return c;
}

// ===================== WIRE FRAMEBUFFER (ENDPOINT BLINK) =====================

void LedMatrix::frameClear()
{
    for (int i = 0; i < (int)LedMatrix::NUM_LEDS; i++)
    {
        s_pathR[i] = s_pathG[i] = s_pathB[i] = 0;
        s_endR[i] = s_endG[i] = s_endB[i] = 0;
        s_isEndpoint[i] = false;
    }
    s_haveFrame = false;
}

void LedMatrix::frameResetBlink()
{
    s_blinkOn = true;
    s_lastBlinkMs = millis();
}

void LedMatrix::framePaintPathIdx(int idx, const RGB &c)
{
    if (idx < 0 || idx >= (int)LedMatrix::NUM_LEDS) return;
    s_pathR[idx] = c.r;
    s_pathG[idx] = c.g;
    s_pathB[idx] = c.b;
}

void LedMatrix::frameMarkEndpointIdx(int idx, const RGB &c)
{
    if (idx < 0 || idx >= (int)LedMatrix::NUM_LEDS) return;
    s_isEndpoint[idx] = true;
    s_endR[idx] = c.r;
    s_endG[idx] = c.g;
    s_endB[idx] = c.b;
}

void LedMatrix::frameApplyToBuffer()
{
    for (int i = 0; i < (int)LedMatrix::NUM_LEDS; i++)
        LedMatrix::strip().setPixelColor((uint16_t)i, LedMatrix::strip().Color(s_pathR[i], s_pathG[i], s_pathB[i]));

    // Overlay endpoints (blink)
    for (int i = 0; i < (int)LedMatrix::NUM_LEDS; i++)
    {
        if (!s_isEndpoint[i]) continue;

        if (s_blinkOn)
            LedMatrix::strip().setPixelColor((uint16_t)i, LedMatrix::strip().Color(s_endR[i], s_endG[i], s_endB[i]));
        else
            LedMatrix::strip().setPixelColor((uint16_t)i, LedMatrix::strip().Color(s_pathR[i], s_pathG[i], s_pathB[i]));
    }

    s_haveFrame = true;
}

void LedMatrix::frameApplyFull()
{
    frameApplyToBuffer();
    LedMatrix::strip().show();
}

void LedMatrix::frameSaveSnapshot()
{
    for (int i = 0; i < (int)NUM_LEDS; i++) {
        s_snapPathR[i]    = s_pathR[i];
        s_snapPathG[i]    = s_pathG[i];
        s_snapPathB[i]    = s_pathB[i];
        s_snapEndR[i]     = s_endR[i];
        s_snapEndG[i]     = s_endG[i];
        s_snapEndB[i]     = s_endB[i];
        s_snapIsEndpoint[i] = s_isEndpoint[i];
    }
    s_haveSnapshot = true;
}

void LedMatrix::frameRestoreSnapshot()
{
    if (!s_haveSnapshot) return;
    for (int i = 0; i < (int)NUM_LEDS; i++) {
        s_pathR[i]    = s_snapPathR[i];
        s_pathG[i]    = s_snapPathG[i];
        s_pathB[i]    = s_snapPathB[i];
        s_endR[i]     = s_snapEndR[i];
        s_endG[i]     = s_snapEndG[i];
        s_endB[i]     = s_snapEndB[i];
        s_isEndpoint[i] = s_snapIsEndpoint[i];
    }
}

bool LedMatrix::frameHasSnapshot()
{
    return s_haveSnapshot;
}

void LedMatrix::frameClearSnapshot()
{
    s_haveSnapshot = false;
}

void LedMatrix::frameDimAll(uint8_t factor)
{
    for (int i = 0; i < (int)NUM_LEDS; i++) {
        s_pathR[i] = (uint8_t)((uint16_t)s_pathR[i] * factor / 255);
        s_pathG[i] = (uint8_t)((uint16_t)s_pathG[i] * factor / 255);
        s_pathB[i] = (uint8_t)((uint16_t)s_pathB[i] * factor / 255);
        s_endR[i]  = (uint8_t)((uint16_t)s_endR[i]  * factor / 255);
        s_endG[i]  = (uint8_t)((uint16_t)s_endG[i]  * factor / 255);
        s_endB[i]  = (uint8_t)((uint16_t)s_endB[i]  * factor / 255);
    }
}

void LedMatrix::frameTick()
{
    if (!s_haveFrame) return;

    uint32_t now = millis();
    if (now - s_lastBlinkMs >= LedMatrix::BLINK_PERIOD_MS)
    {
        s_lastBlinkMs = now;
        s_blinkOn = !s_blinkOn;
        applyEndpointsOnly();
    }
}