#pragma once

#include <Arduino.h>
#include "pin_map.h"
#include <Adafruit_NeoPixel.h>


namespace rgbPatterns {

    // Shows "JUMPER-Z" on M1 (JUMP) and M2 (ER-Z) using a 5x3 pixel font
    void showName(Adafruit_NeoPixel &strip);

    // Full startup animation: comet sweep -> JUMPER-Z name -> flash -> fade
    void startup(Adafruit_NeoPixel &strip);

}