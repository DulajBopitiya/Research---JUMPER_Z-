#include <Arduino.h>
#include "rp_bridge.h"
#include "rp_stm_bridge.h"
#include "osc_detect.h"

void setup() {
    Serial.begin(115200);
    RpBridge::begin();
    StmBridge::begin();
    OscDetect::begin();
}

void loop() {
    RpBridge::loop();
    StmBridge::loop();
    OscDetect::tick();
}
