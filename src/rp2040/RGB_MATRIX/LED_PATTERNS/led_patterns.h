#pragma once

#include <Arduino.h>
#include "pin_map.h"
#include <Adafruit_NeoPixel.h>


namespace rgbPatterns {

    // Legacy: renders "JUMPER-Z" on M1+M2 using a 5×3 pixel font (kept for compatibility).
    void showName(Adafruit_NeoPixel &strip);

    // Boot animation sequence (kept for reference, no longer called by default).
    void startup(Adafruit_NeoPixel &strip);

    // Played when the Bridge port (USBSer1) first connects.
    // Fast green comet sweep → bright flash → fade. ~700 ms total.
    void connectionSuccess(Adafruit_NeoPixel &strip);

    // Played when the Bridge port (USBSer1) disconnects.
    // All LEDs drain to red then fade out. ~600 ms total.
    void connectionLost(Adafruit_NeoPixel &strip);

    // ── Oscilloscope plug/unplug animations ────────────────────────────────
    // Selected via the persistent settings osc_conn_style / osc_disconn_style.
    // JumperZ_SEQ::oscPlugAnimation() dispatches by style number.
    //
    // Connect styles:
    //   0 = OFF (no animation)
    //   1 = Scope Wave   — green sine wave traces across M1+M2 then flash+fade (~800 ms)
    //   2 = Comet Sweep  — cyan→green comet across all 400 LEDs + green burst (~700 ms)
    //   3 = Ripple       — green wave expands outward from M1↔M2 boundary (~525 ms)
    //   4 = Matrix Rain  — green/white drops fall down M1+M2 columns (~750 ms)
    void oscConnectedScopeWave(Adafruit_NeoPixel &strip);
    void oscConnectedComet    (Adafruit_NeoPixel &strip);
    void oscConnectedRipple   (Adafruit_NeoPixel &strip);
    void oscConnectedMatrix   (Adafruit_NeoPixel &strip);

    // Disconnect styles:
    //   0 = OFF
    //   1 = Flatline — amber line on row 2 of M1+M2 then fade   (~400 ms)
    //   2 = Red Fade — full M1+M2 snap to red then fade to off  (~360 ms)
    //   3 = Drain    — amber pane drains from outer edges inward (~380 ms)
    void oscDisconnectedFlatline(Adafruit_NeoPixel &strip);
    void oscDisconnectedRedFade (Adafruit_NeoPixel &strip);
    void oscDisconnectedDrain   (Adafruit_NeoPixel &strip);

}