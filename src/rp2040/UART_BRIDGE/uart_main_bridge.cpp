#include "uart_main_bridge.h"
#include "usb_cdc_config.h"

// SerialPIO(TX_pin, RX_pin)
SerialPIO UARTMainBridge::E_EspUart(ESP32_RP_COM_TX, ESP32_RP_COM_RX);

// ── Oscilloscope sentinel sniffer state ──────────────────────────────────────
// Watches the ESP→USBSer2 stream for FE FD FE FD <01|02> injected by the
// ESP32-side OscDetect. Matched sentinels are swallowed; partial-match prefixes
// that turn out to be real STM32 data are flushed to USBSer2 intact.
static const uint8_t kOscPattern[4] = { 0xFE, 0xFD, 0xFE, 0xFD };
static uint8_t s_sniffState = 0;            // 0..4 — bytes of pattern matched
static uint8_t s_sniffHold[4];              // held bytes during partial match
static UARTMainBridge::OscEventCallback s_oscCb = nullptr;

// Filter `in[n]` through the sentinel sniffer. Writes non-sentinel bytes to
// `out` and returns the count written. `out` must hold at least n + 4 bytes
// (worst case: 4 held bytes from a previous tick get flushed at the start).
static size_t sniffAndStrip(const uint8_t* in, size_t n, uint8_t* out)
{
    size_t outIdx = 0;
    for (size_t i = 0; i < n; i++) {
        uint8_t b = in[i];

        if (s_sniffState < 4) {
            if (b == kOscPattern[s_sniffState]) {
                s_sniffHold[s_sniffState++] = b;
                continue;
            }
            // Mismatch: flush the held prefix to output.
            for (uint8_t h = 0; h < s_sniffState; h++) out[outIdx++] = s_sniffHold[h];
            s_sniffState = 0;
            // The mismatching byte may itself start a fresh sequence.
            if (b == kOscPattern[0]) {
                s_sniffHold[0] = b;
                s_sniffState   = 1;
            } else {
                out[outIdx++] = b;
            }
            continue;
        }

        // s_sniffState == 4 → expecting the event code.
        s_sniffState = 0;
        if (b == 0x01 || b == 0x02) {
            if (s_oscCb) s_oscCb(b == 0x01);
        } else {
            // Not a recognised event — flush the magic prefix and the byte.
            for (uint8_t h = 0; h < 4; h++) out[outIdx++] = s_sniffHold[h];
            out[outIdx++] = b;
        }
    }
    return outIdx;
}

void UARTMainBridge::begin(uint32_t baud) {
    E_EspUart.begin(baud);
}

void UARTMainBridge::sendLine(const char* msg) {
    E_EspUart.println(msg);
}

void UARTMainBridge::onOscEvent(OscEventCallback cb) {
    s_oscCb = cb;
}

void UARTMainBridge::loop() {
    // Transparent byte pipe USBSer2 (OSC_FUN_PORT) <-> ESP32 UART <-> STM32.
    // The only inserted side-channel is the OscDetect sentinel
    // (FE FD FE FD <01|02>) which sniffAndStrip() swallows before USBSer2.

    uint8_t buf[64];
    uint8_t out[72];   // 64 + up to 4 carried held bytes + 4 fresh

    int n = E_EspUart.available();
    if (n > 0) {
        if (n > (int)sizeof(buf)) n = sizeof(buf);
        int got = E_EspUart.readBytes(buf, n);
        if (got > 0) {
            size_t outLen = sniffAndStrip(buf, (size_t)got, out);
            if (outLen > 0 && (bool)USB_CDC_Config::USBSer2) {
                USB_CDC_Config::USBSer2.write(out, outLen);
                // No flush(): TinyUSB auto-ships on next poll. Calling
                // flush() per chunk blocks until the IN endpoint drains
                // and throttles high-rate STM32 streams.
            }
        }
    }

    if ((bool)USB_CDC_Config::USBSer2) {
        int m = USB_CDC_Config::USBSer2.available();
        if (m > 0) {
            if (m > (int)sizeof(buf)) m = sizeof(buf);
            int got = USB_CDC_Config::USBSer2.readBytes(buf, m);
            if (got > 0) E_EspUart.write(buf, got);
        }
    }
}
