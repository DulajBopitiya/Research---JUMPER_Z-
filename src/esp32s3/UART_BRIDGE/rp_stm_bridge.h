#pragma once

#include <Arduino.h>

// ── ESP32-S3 ↔ STM32 UART bridge ─────────────────────────────────────────────
// Physical wires (UART crosses: TX → RX, RX → TX):
//   STM32 TX ──► ESP32-S3 GPIO 45 (RX)   [also Chip K X4 crosspoint]
//   STM32 RX ◄── ESP32-S3 GPIO 46 (TX)   [also Chip K X5 crosspoint]
//
// Uses UART1. Transparent byte pipe:
//   STM32 TX -> UART1 RX (45) -> RpBridge::write() -> UART0 TX -> RP2040 -> USBSer2 -> PC
//   PC -> USBSer2 -> RP2040 -> UART0 RX -> StmBridge::write() -> UART1 TX (46) -> STM32 RX
//
// So a "#A#" sent by Python to the JZ Oscilloscope CDC port lands on STM32 RX
// verbatim, and any data the STM32 streams on its TX comes back on the same
// CDC port byte-for-byte.
//
// Baud rate defaults to 115200 — change STM_UART_BAUD if the STM32 firmware
// uses a different rate.
// ─────────────────────────────────────────────────────────────────────────────


// ESP32 pin roles — pin 45 is the ESP32 RX (reads what STM32 transmits),
// pin 46 is the ESP32 TX (drives what STM32 receives).
#define STM_UART_RX_PIN  45    // ← STM32 TX
#define STM_UART_TX_PIN  46      // → STM32 RX
#define STM_UART_BAUD    115200

namespace StmBridge
{
    void begin();
    void loop();

    // Raw byte write to the STM32 — used by RpBridge::loop() for passthrough.
    void write(const uint8_t* buf, size_t len);
}
