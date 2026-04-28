#include "JumperZ_SEQ.h"

namespace JumperZ_SEQUENCE
{

    static bool s_bridgeWasConnected = false;
    static bool s_animEnabled = false;

    void setAnimEnabled(bool en) { s_animEnabled = en; }
    bool isAnimEnabled()         { return s_animEnabled; }

    using OscPatternFn = void (*)(Adafruit_NeoPixel &);

    static const OscPatternFn kConnFns[] = {
        nullptr,                              // 0 = off
        rgbPatterns::oscConnectedScopeWave,   // 1
        rgbPatterns::oscConnectedComet,       // 2
        rgbPatterns::oscConnectedRipple,      // 3
        rgbPatterns::oscConnectedMatrix,      // 4
    };
    static const OscPatternFn kDisconnFns[] = {
        nullptr,                              // 0 = off
        rgbPatterns::oscDisconnectedFlatline, // 1
        rgbPatterns::oscDisconnectedRedFade,  // 2
        rgbPatterns::oscDisconnectedDrain,    // 3
    };

    void JumperZ_Setup()
    {
        Settings::setup();                              // load EEPROM before anything uses brightness
        USB_CDC_Config::USB_CDC_setup();
        UARTMainBridge::begin(115200);
        LedMatrix::begin(Settings::get().brightness);  // apply saved brightness
        initCH446Q();
        Measurements::setup();
        Measurements::scanI2C();
        JsonBridge::clearFrame();
        JsonBridge::begin(LedMatrix::strip());
        NanoHeader::setup();

        s_animEnabled = Settings::get().conn_anim;

        // Osc plug/unplug arrives as a sentinel sniffed in uart_main_bridge.cpp.
        // Patterns wipe the strip but not the framebuffer, so after the
        // animation we re-push the framebuffer to keep any drawn circuit lit.
        UARTMainBridge::onOscEvent([](bool connected) {
            const Settings::Config &cfg = Settings::get();
            Adafruit_NeoPixel &s = LedMatrix::strip();

            uint8_t style = connected ? cfg.osc_conn_style : cfg.osc_disconn_style;
            const OscPatternFn *table = connected ? kConnFns : kDisconnFns;
            size_t tableLen = connected ? (sizeof(kConnFns)    / sizeof(kConnFns[0]))
                                        : (sizeof(kDisconnFns) / sizeof(kDisconnFns[0]));

            OscPatternFn fn = (style < tableLen) ? table[style] : table[1];
            if (!fn) return;
            fn(s);

            LedMatrix::frameResetBlink();
            LedMatrix::frameApplyFull();
        });
    }

    void JumperZ_Loop()
    {
        bool bridgeNow = (bool)USB_CDC_Config::USBSer1;
        if (bridgeNow != s_bridgeWasConnected) {
            if (s_animEnabled) {
                if (bridgeNow) rgbPatterns::connectionSuccess(LedMatrix::strip());
                else           rgbPatterns::connectionLost(LedMatrix::strip());
            }
            s_bridgeWasConnected = bridgeNow;
        }

        if (USB_CDC_Config::USBSer1.available())
        {
            JsonDocument req;
            DeserializationError err = deserializeJson(req, USB_CDC_Config::USBSer1);

            if (!err)
            {
                JsonBridge::handle(USB_CDC_Config::USBSer1, req);
            }
        }

        JsonBridge::tick();
        CurrentViz::tick();
        NanoHeader::loop();
        UARTMainBridge::loop();

    }
}