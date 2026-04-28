#include "osc_detect.h"
#include "rp_stm_bridge.h"
#include "rp_bridge.h"
#include "driver/gpio.h"

namespace OscDetect
{
    enum State : uint8_t { UNKNOWN = 0, DISCONNECTED = 1, CONNECTED = 2 };

    static const uint32_t SAMPLE_INTERVAL_MS = 5;    // ~200 Hz
    static const uint32_t DEBOUNCE_MS        = 200;  // window for HIGH activity

    static State    s_state         = UNKNOWN;
    static uint32_t s_startMs       = 0;
    static uint32_t s_lastSampleMs  = 0;
    static uint32_t s_lastHighMs    = 0;

    static void emitSentinel(uint8_t event)
    {
        const uint8_t magic[5] = { 0xFE, 0xFD, 0xFE, 0xFD, event };
        RpBridge::write(magic, sizeof(magic));
    }

    void begin()
    {
        // Apply an internal pulldown to the STM-RX pin without disturbing the
        // UART1 routing. pinMode() would re-grab the pin; the IDF GPIO call
        // only touches the pull resistor.
        gpio_set_pull_mode((gpio_num_t)STM_UART_RX_PIN, GPIO_PULLDOWN_ONLY);

        s_state        = UNKNOWN;
        s_startMs      = millis();
        s_lastSampleMs = s_startMs;
        s_lastHighMs   = 0;

        Serial.printf("[OscDetect] presence-detect armed on GPIO %d (pulldown)\n",
                      STM_UART_RX_PIN);
    }

    void tick()
    {
        uint32_t now = millis();
        if ((now - s_lastSampleMs) < SAMPLE_INTERVAL_MS) return;
        s_lastSampleMs = now;

        if (digitalRead(STM_UART_RX_PIN) == HIGH) {
            s_lastHighMs = now;
        }

        // Grace window after begin(): wait DEBOUNCE_MS to gather samples
        // before declaring an initial state.
        if ((now - s_startMs) < DEBOUNCE_MS) return;

        State next = ((now - s_lastHighMs) < DEBOUNCE_MS) ? CONNECTED
                                                          : DISCONNECTED;
        if (next == s_state) return;
        s_state = next;

        if (next == CONNECTED) {
            Serial.printf("[OscDetect] oscilloscope CONNECTED\n");
            emitSentinel(0x01);
        } else {
            Serial.printf("[OscDetect] oscilloscope DISCONNECTED\n");
            emitSentinel(0x02);
        }
    }

    bool isConnected() { return s_state == CONNECTED; }
}
