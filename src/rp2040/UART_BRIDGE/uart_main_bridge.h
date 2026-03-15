#pragma once

#include <Arduino.h>
#include <SerialPIO.h>
#include "pin_map.h"

// ── RP2040 ↔ ESP32-S3 UART bridge ────────────────────────────────────────────
// Physical wires:
//   RP2040 GPIO 19 (TX) ──► ESP32-S3 GPIO 18 (RX)
//   RP2040 GPIO 18 (RX) ◄── ESP32-S3 GPIO 19 (TX)
//
// Uses SerialPIO so Serial1 (GPIO 16/17) remains free for the Nano TTL bridge.
// ─────────────────────────────────────────────────────────────────────────────

class UARTMainBridge
{
public:
    // Call once in setup()
    static void begin(uint32_t baud = 115200);

    // Send a line to the ESP32-S3 (appends '\n')
    static void sendLine(const char* msg);

    // Call every loop() iteration — forwards ESP32 replies to Serial for debug
    static void loop();

    // Raw access for callers that need to read/write manually
    static int  available();
    static int  read();

private:
    // SerialPIO(TX_pin, RX_pin)
    static SerialPIO E_EspUart;
};
