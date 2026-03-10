#pragma once

#include <Arduino.h>
#include "pin_map.h"
#include <Adafruit_NeoPixel.h>


namespace rgbPatterns{

    void startup(Adafruit_NeoPixel &strip);
}