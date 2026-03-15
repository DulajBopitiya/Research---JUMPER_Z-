#include "rp_bridge.h"

// UART1 instance — pins remapped in begin()
static HardwareSerial rpUart(RP_UART_NUM);

// ─────────────────────────────────────────────────────────────────────────────

void RpBridge::begin() {
    rpUart.begin(RP_UART_BAUD, SERIAL_8N1, RP_UART_RX_PIN, RP_UART_TX_PIN);
    Serial.printf("[RpBridge] UART1 ready  RX=%d  TX=%d\n",
                  RP_UART_RX_PIN, RP_UART_TX_PIN);

    // Tell the RP2040 we are up — it will print this via UARTMainBridge::loop()
    rpUart.println("READY");
}

void RpBridge::sendLine(const char* msg) {
    rpUart.println(msg);
}

int RpBridge::available() {
    return rpUart.available();
}

int RpBridge::read() {
    return rpUart.read();
}

// ── private ───────────────────────────────────────────────────────────────────

void RpBridge::handleLine(const String& line) {
    Serial.print("[RP] ");
    Serial.println(line);

    // ── command dispatch ──────────────────────────────────────────────────────
    if (line == "PING") {
        rpUart.println("PONG");

    } else if (line == "TOGGLE") {
        // legacy — kept for compatibility with old RP2040 firmware
        rpUart.println("OK");

    } else {
        // Unknown message — echo back so the RP2040 can detect dropped lines
        rpUart.print("ACK:");
        rpUart.println(line);
    }
}

void RpBridge::loop() {
    while (rpUart.available()) {
        String line = rpUart.readStringUntil('\n');
        line.trim();
        if (line.length() == 0) continue;
        handleLine(line);
    }
}
