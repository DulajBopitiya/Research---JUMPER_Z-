#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>
#include "configuration.h"            // LedMatrix + pin_map
#include "path_mapping_algo.h"        // net[], path[], sfMappings[], chipStatus
#include "nets_to_chip_connections.h" // netsToChipConnectionsFull(), commitPaths()
#include "ch446q_config.h"            // sendAllPaths(), clearAllChips()

// JsonBridge — JSON command handler.
// Owns the wire protocol. LED rendering lives in LedMatrix.
// CH446Q switching lives in ch446q_config / nets_to_chip_connections.
//
// Commands:
//   {"cmd":"ping"}
//   {"cmd":"clear"}               — clear LEDs + all CH446Q connections
//   {"cmd":"wokwi_wires","wires":[...]}  — LED-only visual (unchanged)
//   {"cmd":"connect","nets":[{"nodes":["NANO_D3","TOP_5"],"color":"#0f0"},…]}
//                                 — close physical switches + light endpoints
//   {"cmd":"netlist_query"}       — return current path state
namespace JsonBridge
{
    void begin(Adafruit_NeoPixel &strip);
    void handle(Stream &replyTo, JsonDocument &req);
    void tick();
    void clear();
    void clearFrame();
}