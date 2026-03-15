#pragma once

#include <Arduino.h>

// ── ESP32-S3 ↔ RP2040 UART bridge ────────────────────────────────────────────
// Physical wires (board traces):
//   ESP32-S3 GPIO 45 (RX) ◄── RP2040 GPIO 19 (TX, ESP32_RP_COM_TX)
//   ESP32-S3 GPIO 46 (TX) ──► RP2040 GPIO 18 (RX, ESP32_RP_COM_RX)
//
// ⚠ DO NOT use GPIO 19 or 20 on ESP32-S3 — they are USB D- / D+.
//    Driving them from UART kills USB enumeration.
//
// Uses UART1 with explicit pin assignment.
// UART0 (GPIO 43/44) is the USB-CDC debug monitor — do not use it for this.
// ─────────────────────────────────────────────────────────────────────────────

#define RP_UART_NUM     1
#define RP_UART_RX_PIN  45      // esp32_STM32_Bridge_Rx in pin_map.h
#define RP_UART_TX_PIN  46      // esp32_STM32_Bridge_Tx in pin_map.h
#define RP_UART_BAUD    115200

class RpBridge
{
public:
    // Call once in setup()
    static void begin();

    // Call every loop() — reads lines from RP2040 and dispatches them
    static void loop();

    // Send a newline-terminated message to the RP2040
    static void sendLine(const char* msg);

    // Raw byte access
    static int  available();
    static int  read();

private:
    // Dispatches a complete line received from the RP2040
    static void handleLine(const String& line);
};
