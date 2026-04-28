#pragma once
#include <Arduino.h>

// Settings — persistent board configuration stored in the RP2040's on-chip
// flash via the earlephilhower EEPROM emulation library.  No external I2C
// EEPROM chip required.  Values survive power-cycles.
//
// Call Settings::setup() first in JumperZ_Setup() so that brightness is
// loaded before LedMatrix::begin() is called.
//
// JSON API (via JZ NETSH / USBSer1):
//   {"cmd":"settings"}                                → get all settings + eeprom_ok
//   {"cmd":"settings","action":"get"}                 → same as above
//   {"cmd":"settings","action":"set","brightness":80} → update field(s), persist
//   {"cmd":"settings","action":"verify"}              → read-back check from EEPROM
//   {"cmd":"settings","action":"reset"}               → restore factory defaults
//
// Settable fields:
//   brightness        uint8_t 0–255  LED strip global brightness        (default 50)
//   conn_anim         bool           USB-connect animation              (default false)
//   disconn_anim      bool           USB-disconnect animation           (default false)
//   osc_conn_style    uint8_t 0–4    Oscilloscope plug-in animation     (default 1)
//                                       0=off  1=ScopeWave  2=Comet
//                                       3=Ripple  4=MatrixRain
//   osc_disconn_style uint8_t 0–3    Oscilloscope unplug animation      (default 1)
//                                       0=off  1=Flatline  2=RedFade  3=Drain

namespace Settings {

// Magic number written alongside the config.
// Bump this value to force a one-time reset to factory defaults on next boot.
static constexpr uint32_t SETTINGS_MAGIC      = 0xFAB10002UL;

// Byte address inside the CAT24C256 where the Config struct is stored.
static constexpr uint16_t SETTINGS_EEPROM_ADDR = 0x0000;

// ── Persistent config struct ──────────────────────────────────────────────
// Must fit within one 64-byte EEPROM page (currently 16 bytes).
// To add a new field: append before _reserved[], shrink _reserved[] by the
// same byte count, and bump SETTINGS_MAGIC.
struct Config {
    uint32_t magic;             // Must equal SETTINGS_MAGIC
    uint8_t  brightness;        // Global LED brightness 0–255      (default 50)
    bool     conn_anim;         // USB-connect animation             (default false)
    bool     disconn_anim;      // USB-disconnect animation          (default false)
    uint8_t  osc_conn_style;    // Oscilloscope plug-in animation    (default 1)
    uint8_t  osc_disconn_style; // Oscilloscope unplug animation     (default 1)
    uint8_t  _reserved[7];      // Reserved — zeroed; available for future fields
};
static_assert(sizeof(Config) <= 64, "Config must fit within one EEPROM page");

// ── API ───────────────────────────────────────────────────────────────────

// Initialise Wire0 and load settings from the external EEPROM.
// If data is missing or invalid (wrong magic), writes factory defaults.
// Must be called before any other Settings function.
void setup();

// Return a reference to the in-RAM config (read/write).
// Call save() after any mutation you want to persist to EEPROM.
Config &get();

// Write the in-RAM config to the external EEPROM.
// Returns true on success (EEPROM ACKed).
bool save();

// Restore factory defaults in RAM and write them to EEPROM.
// Returns true on success.
bool reset();

// Read the Config back from EEPROM and compare to RAM.
// Returns true if the EEPROM contents match the in-RAM config exactly.
bool verify();

// Returns true if the EEPROM was reachable during setup().
// False means Wire/I2C communication failed — settings live in RAM only.
bool eepromOk();

} // namespace Settings
