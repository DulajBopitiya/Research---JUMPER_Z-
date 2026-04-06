#pragma once

#include <Arduino.h>
#include "pin_map.h"
#include <Wire.h>

// ---------------------------------------------------------------------------
// INA219AIDR current/voltage sensor driver
//
// Two sensors share Wire0 (GPIO 4 SDA, GPIO 5 SCL).
// They are physically connected to the crosspoint matrix via Chip L:
//   Chip L  X0 = ISENSE_MINUS  (INA219 IN-)
//   Chip L  X1 = ISENSE_PLUS   (INA219 IN+)
//
// I2C addresses (7-bit):
//   Sensor 0 → INA219_ADDR_0  (default 0x40, 8-bit write = 0x80)
//   Sensor 1 → INA219_ADDR_1  (default 0x41, 8-bit write = 0x82)
// Change these to match the solder-bridge configuration on your board.
//
// Shunt resistor:
//   INA219_SHUNT_OHMS — adjust to match the actual shunt on the board.
//   The calibration register is computed from this value at runtime.
// ---------------------------------------------------------------------------

#define INA219_ADDR_0       0x40    // Sensor 0: A1=GND, A0=GND
#define INA219_ADDR_1       0x41    // Sensor 1: A1=GND, A0=VS

// Shunt resistor value in ohms — update this to match your hardware.
// Typical values: 0.1Ω, 0.01Ω. Affects current/power scaling only.
// Shunt voltage reading (shuntMv) is always returned raw.
#define INA219_SHUNT_OHMS   2.0f

// Maximum expected current (A) — determines Current_LSB resolution.
#define INA219_MAX_CURRENT_A  3.2f


namespace Measurements
{
    struct Reading {
        float shuntMv;    // shunt voltage in mV (raw, always valid)
        float busV;       // bus voltage in V
        float currentMa;  // current in mA (requires correct SHUNT_OHMS)
        float powerMw;    // power in mW   (requires correct SHUNT_OHMS)
        bool  valid;      // false if sensor did not respond
    };

    // Initialise Wire0 and configure both INA219 sensors.
    // Call once during setup().
    void setup();

    // Read from one sensor. sensorIdx = 0 or 1.
    // Returns Reading with valid=false if the sensor does not ACK.
    Reading read(uint8_t sensorIdx);

    // Scan Wire0 for responding devices and print to Serial (debug helper).
    void scanI2C();
}
