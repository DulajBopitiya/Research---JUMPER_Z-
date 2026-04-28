#include "rp_stm_bridge.h"
#include "rp_bridge.h"

// UART1 — STM32 TX → GPIO 45 (ESP RX), STM32 RX ← GPIO 46 (ESP TX)
static HardwareSerial stmUart(1);

namespace StmBridge
{
    void begin()
    {
        stmUart.begin(STM_UART_BAUD, SERIAL_8N1, STM_UART_RX_PIN, STM_UART_TX_PIN);
        Serial.printf("[StmBridge] UART1 ready  RX=%d (←STM TX)  TX=%d (→STM RX)\n",
                      STM_UART_RX_PIN, STM_UART_TX_PIN);
    }

    void write(const uint8_t* buf, size_t len)
    {
        stmUart.write(buf, len);
    }

    // ── byte passthrough: UART1 (STM32)  →  UART0 (RP2040) ───────────────────
    void loop()
    {
        uint8_t buf[128];
        int n = stmUart.available();
        if (n <= 0) return;
        if (n > (int)sizeof(buf)) n = sizeof(buf);
        int got = stmUart.readBytes(buf, n);
        if (got > 0) RpBridge::write(buf, got);
    }
}
