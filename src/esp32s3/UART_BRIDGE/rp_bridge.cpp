#include "rp_bridge.h"
#include "rp_stm_bridge.h"

// UART0 — U0TXD (GPIO 43) / U0RXD (GPIO 44), wired to RP2040 GPIO 18/19
static HardwareSerial rpUart(0);

void RpBridge::begin() {
    rpUart.begin(RP_UART_BAUD, SERIAL_8N1, 44, 43);  // RX=44, TX=43
    Serial.printf("[RpBridge] UART0 ready  RX=44 (U0RXD)  TX=43 (U0TXD)\n");
    // No greeting is written to rpUart — UART0 is a raw byte pipe; any stray
    // print would land on the STM32 verbatim and corrupt the stream.
}

void RpBridge::write(const uint8_t* buf, size_t len) {
    rpUart.write(buf, len);
}

// ── byte passthrough: UART0 (RP2040)  →  UART1 (STM32) ───────────────────────

void RpBridge::loop() {
    uint8_t buf[128];
    int n = rpUart.available();
    if (n <= 0) return;
    if (n > (int)sizeof(buf)) n = sizeof(buf);
    int got = rpUart.readBytes(buf, n);
    if (got > 0) StmBridge::write(buf, got);
}
