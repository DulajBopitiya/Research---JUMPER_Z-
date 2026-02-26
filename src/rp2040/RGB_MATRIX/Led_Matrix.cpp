#include "Led_Matrix.h"
#include "configuration.h"   // RGB_LED_PIN, NEO_GRB, etc (from your project)


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