#pragma once

#include <Arduino.h>
#include <SerialPIO.h>
#include "pin_map.h"

// ── RP2040 ↔ ESP32-S3 UART bridge ────────────────────────────────────────────
// Physical wires:
//   RP2040 GPIO 19 (TX) ──► ESP32-S3 GPIO 45 (RX)
//   RP2040 GPIO 18 (RX) ◄── ESP32-S3 GPIO 46 (TX)
//
// Uses SerialPIO so Serial1 (GPIO 16/17) remains free for the Nano TTL bridge.
//
// This bridge is a transparent byte pipe between the USB "JZ Oscilloscope"
// CDC port (USBSer2, a.k.a. OSC_FUN_PORT on the host) and the STM32 USART,
// via the ESP32-S3.  The ESP32 does the same passthrough between UART0 and
// UART1, so the whole path is byte-for-byte — ideal for oscilloscope /
// function-generator streams or any other host<->STM32 traffic.
// ─────────────────────────────────────────────────────────────────────────────

class UARTMainBridge
{
public:
    // Callback fired when the ESP32 reports an oscilloscope plug/unplug event
    // (5-byte sentinel FE FD FE FD <01|02> in the ESP→USBSer2 stream — those
    // bytes are swallowed and never reach Python). `connected` = true on plug,
    // false on unplug. Register from JumperZ_SEQ to dispatch an LED animation.
    typedef void (*OscEventCallback)(bool connected);

    // Call once in setup()
    static void begin(uint32_t baud = 115200);

    // Call every loop() iteration — shuttles raw bytes between USBSer2 and
    // the ESP32 UART in both directions.
    static void loop();

    // Send a newline-terminated string toward the STM32 via the byte pipe.
    // Used by the JSON `stm_cmd` helper; the bytes flow through verbatim.
    static void sendLine(const char* msg);

    // Register the oscilloscope plug/unplug handler. Pass nullptr to clear.
    static void onOscEvent(OscEventCallback cb);

private:
    // SerialPIO(TX_pin, RX_pin)
    static SerialPIO E_EspUart;
};
