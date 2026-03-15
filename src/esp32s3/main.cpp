#include <Arduino.h>
#include "rp_bridge.h"

void setup() {
    Serial.begin(115200);
    RpBridge::begin();
}

void loop() {
    RpBridge::loop();
}
