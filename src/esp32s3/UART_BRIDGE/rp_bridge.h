#pragma once

#include <Arduino.h>

// ── ESP32-S3 ↔ RP2040 UART bridge ────────────────────────────────────────────
// Physical wires (board traces):
//   ESP32-S3 U0TXD (GPIO 43) ──► RP2040 GPIO 18 (RX, ESP32_RP_COM_RX)
//   ESP32-S3 U0RXD (GPIO 44) ◄── RP2040 GPIO 19 (TX, ESP32_RP_COM_TX)
//
// Uses UART0 (HardwareSerial 0, default GPIO 43 TX / 44 RX).
//
// This bridge is half of a transparent byte pipe:
//
//   PC ──USB──► RP2040 USBSer2 ──PIO UART──► ESP32 UART0 ──► ESP32 UART1 ──► STM32
//   PC ◄──USB── RP2040 USBSer2 ◄──PIO UART── ESP32 UART0 ◄── ESP32 UART1 ◄── STM32
//
// Every byte received on UART0 is forwarded raw to UART1 via StmBridge, and
// vice versa.  No framing, no parsing, no PING/PONG handshakes.
//
// One exception: OscDetect (osc_detect.cpp) injects a 5-byte sentinel into
// the ESP→RP path on oscilloscope plug/unplug events:
//     FE FD FE FD 01   = oscilloscope module connected
//     FE FD FE FD 02   = oscilloscope module disconnected
// The RP2040 sniffs this sequence in uart_main_bridge.cpp, swallows it, and
// triggers an LED animation. Real STM32 traffic containing the same FE FD FE
// FD prefix followed by any non-event byte is held briefly and forwarded
// intact — false positives cost nothing beyond a tiny bit of latency.
// ─────────────────────────────────────────────────────────────────────────────

#define RP_UART_BAUD    115200

class RpBridge
{
public:
    static void begin();
    static void loop();

    // Forward raw bytes to the RP2040 (called by StmBridge passthrough).
    static void write(const uint8_t* buf, size_t len);
};
