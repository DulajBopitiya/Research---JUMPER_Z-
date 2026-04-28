#pragma once

#include <Arduino.h>

// ── Oscilloscope module presence detection ───────────────────────────────────
// The oscilloscope module mates to the main board through magnetic pogo pins
// that carry both power and the STM32 USART. When the module is plugged in and
// powered, the STM32 TX line drives the ESP32 RX pin (GPIO 45) HIGH while idle
// and toggles HIGH/LOW during transmission. When the module is unmated the
// pin floats; an internal pulldown on the ESP32 settles it LOW.
//
// OscDetect samples GPIO 45 at ~200 Hz. If any HIGH reading appears within the
// last DEBOUNCE_MS window → CONNECTED. If only LOW samples for that window →
// DISCONNECTED. Edge transitions are reported to the RP2040 via a 5-byte
// sentinel injected into the UART0 stream:
//
//     FE FD FE FD 01   = oscilloscope module connected
//     FE FD FE FD 02   = oscilloscope module disconnected
//
// The RP2040 (uart_main_bridge.cpp) sniffs the ESP→USBSer2 byte stream for
// this sequence, swallows it, and dispatches an LED animation. Real STM32
// data starting with FE FD FE FD followed by a non-event byte is forwarded
// intact (the sniffer holds and re-emits the prefix on mismatch).
// ─────────────────────────────────────────────────────────────────────────────

namespace OscDetect
{
    // Call once after StmBridge::begin().
    void begin();

    // Call every loop() iteration — cheap, sample-and-debounce only.
    void tick();

    // Latest debounced state.
    bool isConnected();
}
