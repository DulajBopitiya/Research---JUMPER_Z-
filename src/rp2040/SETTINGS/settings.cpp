#include "settings.h"
#include <EEPROM.h>
#include <string.h>  // memcmp

// ── RP2040 flash-backed EEPROM emulation ─────────────────────────────────────
// Uses the earlephilhower Arduino-Pico EEPROM library which backs a RAM buffer
// with a dedicated flash page.  EEPROM.begin() loads flash → RAM; EEPROM.put()
// writes to RAM; EEPROM.commit() flushes RAM → flash.
// No external I2C chip or Wire bus required.
// ─────────────────────────────────────────────────────────────────────────────

namespace Settings {

static constexpr uint16_t EEPROM_SIZE = 64;   // bytes to allocate from flash

static Config s_cfg;
static bool   s_eepromOk = false;

static const Config kDefaults = {
    /* magic             */ SETTINGS_MAGIC,
    /* brightness        */ 50,
    /* conn_anim         */ false,
    /* disconn_anim      */ false,
    /* osc_conn_style    */ 1,    // ScopeWave (current behaviour)
    /* osc_disconn_style */ 1,    // Flatline  (current behaviour)
    /* _reserved         */ {0, 0, 0, 0, 0, 0, 0},
};

// ── Public API ────────────────────────────────────────────────────────────

void setup()
{
    EEPROM.begin(EEPROM_SIZE);

    Config tmp;
    EEPROM.get(SETTINGS_EEPROM_ADDR, tmp);

    if (tmp.magic == SETTINGS_MAGIC) {
        s_cfg      = tmp;
        s_eepromOk = true;
    } else {
        // First boot or stale magic — write defaults to flash.
        s_cfg = kDefaults;
        EEPROM.put(SETTINGS_EEPROM_ADDR, s_cfg);
        s_eepromOk = EEPROM.commit();
    }
}

Config &get() { return s_cfg; }

bool eepromOk() { return s_eepromOk; }

bool save()
{
    s_cfg.magic = SETTINGS_MAGIC;
    EEPROM.put(SETTINGS_EEPROM_ADDR, s_cfg);
    s_eepromOk = EEPROM.commit();
    return s_eepromOk;
}

bool reset()
{
    s_cfg = kDefaults;
    EEPROM.put(SETTINGS_EEPROM_ADDR, s_cfg);
    s_eepromOk = EEPROM.commit();
    return s_eepromOk;
}

bool verify()
{
    Config tmp;
    EEPROM.get(SETTINGS_EEPROM_ADDR, tmp);
    return (memcmp(&s_cfg, &tmp, sizeof(Config)) == 0);
}

} // namespace Settings
