#include "measurements.h"

// ---------------------------------------------------------------------------
// INA219 register map
// ---------------------------------------------------------------------------
#define REG_CONFIG   0x00
#define REG_SHUNT    0x01   // shunt voltage, 1 LSB = 10 μV (PGA=8, ±320 mV)
#define REG_BUS      0x02   // bus voltage,   1 LSB =  4 mV,  bits[15:3]
#define REG_POWER    0x03
#define REG_CURRENT  0x04
#define REG_CALIB    0x05

// Default configuration:
//   BRNG  = 1   → 32 V bus range
//   PGA   = 8   → ±320 mV shunt range
//   BADC  = 12-bit (532 μs conversion)
//   SADC  = 12-bit (532 μs conversion)
//   Mode  = 111 → continuous shunt + bus
#define INA219_CONFIG_VAL  0x399F

// ---------------------------------------------------------------------------
// Calibration
//   Current_LSB = MAX_CURRENT / 2^15
//   CAL         = trunc(0.04096 / (Current_LSB × Rshunt))
// ---------------------------------------------------------------------------
static const float s_currentLsb = INA219_MAX_CURRENT_A / 32768.0f;  // A/bit (used for CAL only)

static uint16_t computeCalib()
{
    float cal = 0.04096f / (s_currentLsb * INA219_SHUNT_OHMS);
    return (uint16_t)cal;
}

static const uint8_t s_addresses[2] = { INA219_ADDR_0, INA219_ADDR_1 };

// ---------------------------------------------------------------------------
// Low-level I2C helpers
// ---------------------------------------------------------------------------
static bool writeReg16(uint8_t addr, uint8_t reg, uint16_t value)
{
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write((uint8_t)(value >> 8));
    Wire.write((uint8_t)(value & 0xFF));
    return Wire.endTransmission() == 0;
}

static bool readReg16(uint8_t addr, uint8_t reg, uint16_t &out)
{
    Wire.beginTransmission(addr);
    Wire.write(reg);
    if (Wire.endTransmission(false) != 0) return false;

    Wire.requestFrom((uint8_t)addr, (uint8_t)2);
    if (Wire.available() < 2) return false;

    out = ((uint16_t)Wire.read() << 8) | Wire.read();
    return true;
}

static void configureSensor(uint8_t addr)
{
    writeReg16(addr, REG_CONFIG, INA219_CONFIG_VAL);
    writeReg16(addr, REG_CALIB,  computeCalib());
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
void Measurements::setup()
{
    Wire.setSDA(INA219_SDA_PIN);
    Wire.setSCL(INA219_SCL_PIN);
    Wire.begin();
    Wire.setClock(400000);   // 400 kHz fast-mode

    configureSensor(INA219_ADDR_0);
    configureSensor(INA219_ADDR_1);
}

Measurements::Reading Measurements::read(uint8_t sensorIdx)
{
    Reading r{};
    r.valid = false;

    if (sensorIdx > 1) return r;
    uint8_t addr = s_addresses[sensorIdx];

    // Re-apply calibration in case a reset occurred
    configureSensor(addr);
    delay(2);  // allow one conversion cycle (~1.1 ms each)

    uint16_t raw;

    // Shunt voltage: signed, 1 LSB = 10 μV (PGA=8 default)
    if (!readReg16(addr, REG_SHUNT, raw)) return r;
    r.shuntMv = (int16_t)raw * 0.01f;   // 10 μV → mV

    // Bus voltage: bits [15:3], 1 LSB = 4 mV; skip CNVR/OVF bits
    if (!readReg16(addr, REG_BUS, raw)) return r;
    r.busV = (float)((raw >> 3) & 0x1FFF) * 0.004f;

    // Current: compute directly from shunt voltage to avoid INA219 register
    // integer truncation (CAL=209 is too coarse for sub-mA readings).
    // shuntMv / SHUNT_OHMS  →  mV / Ω = mA  ✓
    r.currentMa = r.shuntMv / INA219_SHUNT_OHMS;

    // Power: V × mA = mW  ✓
    r.powerMw = r.busV * r.currentMa;

    r.valid = true;
    return r;
}

void Measurements::scanI2C()
{
    Serial.println("[I2C scan]");
    for (uint8_t a = 1; a < 127; a++) {
        Wire.beginTransmission(a);
        if (Wire.endTransmission() == 0) {
            Serial.print("  device at 0x");
            Serial.println(a, HEX);
        }
    }
    Serial.println("[scan done]");
}
