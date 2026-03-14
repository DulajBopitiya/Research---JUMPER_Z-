#include "nano_header.h"

// Serial.begin() is NOT called — built-in Serial CDC is excluded from the descriptor.
// Only 3 user CDCs exist (CFG_TUD_CDC = 3):
//   CDC 0 = USBSer1  "JZ NETSH"
//   CDC 1 = USBSer3  "JZ TTL"   ← this one
//   CDC 2 = USBSer2  "JZ Oscilloscope"
#define TTL_CDC_IDX  2

namespace NanoHeader
{
    static uint8_t  buf[256];
    static bool     last_dtr   = false;
    static uint32_t last_baud  = 0;

    static bool     rst_active = false;
    static uint32_t rst_timer  = 0;

    static bool cdc_dtr() {
        return tud_cdc_n_get_line_state(TTL_CDC_IDX) & 0x01;
    }

    static uint32_t cdc_baud() {
        cdc_line_coding_t lc;
        tud_cdc_n_get_line_coding(TTL_CDC_IDX, &lc);
        return lc.bit_rate;
    }

    static void sync_baud(uint32_t baud)
    {
        if (baud == last_baud || baud < 300) return;
        last_baud = baud;
        Serial1.end();
        Serial1.setTX(NANO_UART_TX);
        Serial1.setRX(NANO_UART_RX);
        Serial1.begin(baud);
    }

    static void handle_reset_sm()
    {
        if (!rst_active) return;
        if (millis() - rst_timer >= 100) {
            digitalWrite(NANO_RST_PIN, HIGH);
            while (Serial1.available()) Serial1.read();
            rst_active = false;
        }
    }

    static void start_reset()
    {
        digitalWrite(NANO_RST_PIN, LOW);
        rst_timer  = millis();
        rst_active = true;
    }

    void setup()
    {
        pinMode(MUX_SWITCH, OUTPUT);
        digitalWrite(MUX_SWITCH, LOW);

        pinMode(NANO_RST_PIN, OUTPUT);
        digitalWrite(NANO_RST_PIN, HIGH);

        // Serial1.setTX(NANO_UART_TX);
        // Serial1.setRX(NANO_UART_RX);
        Serial1.begin(57600);
        last_baud = 57600;
    }

    void loop()
    {
        // Wait for USB enumeration before touching CDC
        if (!tud_mounted()) return;

        handle_reset_sm();

        // Sync Serial1 baud to whatever avrdude set on the TTL port
        uint32_t new_baud = cdc_baud();
        sync_baud(new_baud);

        // DTR rising edge → reset Nano into bootloader
        bool dtr = cdc_dtr();
        if (dtr && !last_dtr) {
            sync_baud(cdc_baud());
            start_reset();
        }
        last_dtr = dtr;

        // USB → Nano: hold while RST is LOW
        if (!rst_active) {
            int n = (int)tud_cdc_n_available(TTL_CDC_IDX);
            if (n > 0) {
                if (n > (int)sizeof(buf)) n = sizeof(buf);
                n = tud_cdc_n_read(TTL_CDC_IDX, buf, n);
                if (n > 0) Serial1.write(buf, n);
            }
        } else {
            // Drain USB during RST LOW so avrdude buffer stays clean
            uint8_t tmp[64];
            while (tud_cdc_n_available(TTL_CDC_IDX))
                tud_cdc_n_read(TTL_CDC_IDX, tmp, sizeof(tmp));
        }

        // Nano → USB: same gate
        if (!rst_active) {
            int n = Serial1.available();
            if (n > 0) {
                if (n > (int)sizeof(buf)) n = sizeof(buf);
                n = Serial1.readBytes((char*)buf, n);
                if (n > 0) {
                    tud_cdc_n_write(TTL_CDC_IDX, buf, n);
                    tud_cdc_n_write_flush(TTL_CDC_IDX);
                }
            }
        }
    }
}
