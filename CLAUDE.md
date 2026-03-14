# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JumperZ is a dual-microcontroller prototyping board firmware. The RP2040 is the primary controller handling USB, LED visualization, circuit path logic, and hardware control. The ESP32-S3 is a secondary bridge controller.

## Build Commands

Uses **PlatformIO**. Two environments are defined in `platformio.ini`:

```bash
# Build RP2040 firmware
pio run -e jumper_zero_RP2040

# Build ESP32-S3 firmware
pio run -e jumper_zero_ESP32S3

# Upload RP2040 (uses picotool)
pio run -e jumper_zero_RP2040 -t upload

# Upload ESP32-S3
pio run -e jumper_zero_ESP32S3 -t upload

# Monitor serial (RP2040)
pio device monitor -e jumper_zero_RP2040

# Run tests
pio test -e jumper_zero_RP2040
```

Source files are conditionally compiled per platform using `build_src_filter` in `platformio.ini` — `src/rp2040/` only builds for the RP2040 environment, and `src/esp32s3/` only builds for the ESP32-S3 environment.

## Architecture

### RP2040 Control Flow

```
setup() → JumperZ_SEQ::JumperZ_Setup()
  ├── USB_CDC_Config::USB_CDC_setup()   # 3 USB serial ports via TinyUSB
  ├── LedMatrix::begin(50)              # 400x WS2812B LEDs
  └── JsonBridge::begin()

loop() → JumperZ_SEQ::JumperZ_Loop()
  ├── Read JSON from USBSer1
  ├── JsonBridge::handle()              # Process "ping", "clear", "wokwi_wires"
  └── JsonBridge::tick()                # Blink animation at 350ms
```

### USB CDC Ports (RP2040)

Three USB serial interfaces over a single USB connection (TinyUSB, 4 CDC descriptors):
- **USBSer1** — Main JSON control channel ("JumperZ Control")
- **USBSer2** — Oscilloscope data ("JZ Oscilloscope")
- **USBSer3** — TTL serial bridge to Arduino Nano ("JZ TTL")

Custom TinyUSB config lives in `include/custom_tusb_config.h`.

### JSON Command Protocol

Commands are sent as JSON objects to USBSer1:

| Command | Description |
|---------|-------------|
| `{"cmd":"ping"}` | Returns device info and LED count |
| `{"cmd":"clear"}` | Clears all LEDs |
| `{"cmd":"wokwi_wires","wires":[...]}` | Renders circuit paths on LED matrix |

For `wokwi_wires`, wire paths are painted steady and endpoints blink at 350ms. Wire points use `["T",col,row]` (top rail), `["B",col,row]` (bottom rail), `["M1",col,row]`, `["M2",col,row]` coordinates.

### LED Matrix (`src/rp2040/RGB_MATRIX/`)

400 WS2812B LEDs on GPIO 25. Logical layout:
- **Top rails:** 2 rows × 25 columns
- **Middle section 1 & 2:** 5 rows × 30 columns each
- **Bottom rails:** 2 rows × 25 columns

`LedMatrix` holds a framebuffer and provides `setLED()`, `showAll()`, and blink endpoint methods. `JsonBridge` maps wire coordinates to LED indices.

### Pin Mapping (`src/rp2040/pin_map/pin_map.h`)

249 logical pins defined as an enum and lookup table, covering:
- Breadboard nodes (TOP_1–30, BOTTOM_1–30)
- Arduino Nano header (24 pins)
- External 40-pin connector (EXT_PIN_1–35)
- Power rails (3.3V, 5V, 8V+/−, GND)
- Measurements (DAC0/1, ADC0–3, current sense)
- RP2040 internal GPIOs

`src/rp2040/pin_map/configuration.h` includes all subsystem headers.

### CH446Q Multiplexer (`src/rp2040/CH446Q_HANDLER/`)

The CH446Q analog crosspoint switch chips form the breadboard connectivity matrix. Control via:
- **DAT:** GPIO 14
- **CK:** GPIO 15
- **Reset:** GPIO 24
- **MUX select:** GPIO 0

### Path Finding (`src/rp2040/PATH_FINDING/`)

`netStruct` defines circuit netlists with nodes, bridges, power flags, intersection tracking, and LED colors. `nanoStatus` tracks Arduino Nano pin connection states across CH446Q chips I/J/K/L.

### UART Bridge (RP2040 ↔ ESP32-S3)

RP2040 GPIO 16 (TX) / GPIO 17 (RX) → ESP32-S3 GPIO 18 (RX) / GPIO 19 (TX). Simple command protocol: `"TOGGLE\n"` → ESP32-S3 toggles GPIO 40, responds `"OK\n"`.

## Custom Board Definitions

Custom board JSON files in `boards/`:
- `jumper_z_rp2040.json` — VID `0x2E8A`, PID `0x000A`, 2MB flash, 262KB RAM
- `jumper_z_esp32s3.json` — VID `0x303A`, PID `0x1001`, 8MB flash QIO

Variant pin definitions in `Variants/RP2040_VARIANT/` and `Variants/ESP32S3_VARIANT/`.

## Libraries

- **Adafruit NeoPixel** — WS2812B LED strip control
- **Adafruit TinyUSB Library** — Multi-CDC USB serial
- **ArduinoJson** — JSON command parsing/serialization
