#pragma once
#include <Arduino.h>

// CurrentViz — animated current-flow visualization on the LED matrix.
//
// Animates a comet spark flowing in the direction of conventional current
// (high potential → low potential) along each active net's bridge connections.
//
// Direction is determined automatically by propagating known supply voltages
// through the net graph:
//   GND  (node 100) = 0 V
//   3.3V (node 103) = 3.3 V
//   5V   (node 105) = 5.0 V
//
// If a bridge can't be reached from any supply node (both node voltages
// unknown), it falls back to a bidirectional animation so something is
// always visible.
//
// Only breadboard nodes (TOP_1–30 → M1 row 0, BOTTOM_1–30 → M2 row 0) have
// LED positions.  Bridges involving GND, 5V, NANO pins, etc. are used for
// voltage propagation but not drawn (those nodes have no LEDs).
//
// JSON interface (send to USBSer1 / "JZ NETSH"):
//   {"cmd":"current_viz","enable":true}             // on, speed = 1.0
//   {"cmd":"current_viz","enable":true,"speed":2.0} // on, double speed
//   {"cmd":"current_viz","enable":false}            // off, restore frame
//
// Must call CurrentViz::tick() from JumperZ_Loop().

namespace CurrentViz
{
    // Enable or disable animation.
    // speed: 1.0 = normal (~750 ms full cycle), 2.0 = twice as fast.
    void enable(bool on, float speed = 1.0f);

    bool isEnabled();

    // Call every iteration of JumperZ_Loop().
    // Internally rate-limited to ~33 fps; no-op when disabled.
    void tick();
}
