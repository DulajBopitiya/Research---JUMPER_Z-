#pragma once

#include <Arduino.h>
#include "pin_map.h"
#include <Adafruit_NeoPixel.h>


namespace rgbPatterns {

    // Legacy: renders "JUMPER-Z" on M1+M2 using a 5×3 pixel font (kept for compatibility).
    void showName(Adafruit_NeoPixel &strip);

    // Boot animation sequence:
    //   1. Rainbow comet sweep across all 400 LEDs (~840 ms)
    //   2. "FABVOLT" flashes in letter-by-letter on M1 in gold (~1.1 s)
    //   3. FABVOLT breathes on M1 (~1.5 s) while "PROTOMATRIX V1" scrolls
    //      right-to-left on M2 in ice-blue (~1.3 s)
    //   4. Gold + ice-blue sparkle fade (~1.5 s)
    void startup(Adafruit_NeoPixel &strip);

}