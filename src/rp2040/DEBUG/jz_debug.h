#pragma once

// jz_debug.h — JumperZ CH446Q + path-map debug output
//
// Usage (from loop or a JSON command):
//   JZDebug::printAll();           // dump everything to Serial
//   JZDebug::printChipSummary();   // one-line per chip: which X pins are active
//   JZDebug::printChipMap();       // X/Y grid for every chip
//   JZDebug::printPaths();         // all committed paths with node/chip/x/y hops
//   JZDebug::printNets();          // all configured nets
//
// All functions default to Serial but accept any Stream& (e.g. USBSer1).

#include <Arduino.h>

namespace JZDebug
{
    // One-liner per chip showing how many crosspoints are active
    void printChipSummary(Stream &out = Serial);

    // Per-chip X-Y crosspoint grid  (rows = Y bus 0-7, cols = X bus 0-15)
    void printChipMap(Stream &out = Serial);

    // All entries in path[0..numberOfPaths-1] with type, nodes, hops
    void printPaths(Stream &out = Serial);

    // All net[] entries that have at least one node
    void printNets(Stream &out = Serial);

    // Dump everything in one call
    void printAll(Stream &out = Serial);
}
