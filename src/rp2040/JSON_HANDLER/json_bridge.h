#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>
#include "configuration.h"   // for LedMatrix::NUM_LEDS + mapping funcs

// Owns JSON protocol only. LED mapping / blinking lives in LedMatrix.
namespace JsonBridge
{
    // Init (kept for compatibility; strip is owned by LedMatrix)
    void begin(Adafruit_NeoPixel &strip);

    // Handle one parsed JSON request and reply to the same stream
    void handle(Stream &replyTo, JsonDocument &req);

    // Non-blocking blink update (call each loop)
    void tick();

    // Optional helper if you want to clear via code
    void clear();
    void clearFrame(); // clears LedMatrix framebuffer but doesn't update strip immediately
}