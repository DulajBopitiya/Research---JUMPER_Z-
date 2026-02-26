
#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>

// Owns JSON protocol + LED frame + blink logic
namespace JsonBridge
{
   
    // Give module access to your NeoPixel strip (created in main.cpp)
    void begin(Adafruit_NeoPixel &strip);

    // Handle one parsed JSON request and reply to the same stream
    void handle(Stream &replyTo, JsonDocument &req);

    // Non-blocking blink update (call each loop)
    void tick();

    // Optional helper if you want to clear via code
    void clear();
    void clearFrame(); // clears internal framebuffers but doesn't update strip immediately
}