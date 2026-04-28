# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JumperZ is a dual-microcontroller prototyping board firmware. The RP2040 is the primary controller handling USB, LED visualization, circuit path logic, hardware control, and current/voltage measurement. The ESP32-S3 is a secondary bridge controller.

## Build Commands

Uses **PlatformIO** with the earlephilhower Arduino-Pico core. Two environments are defined in `platformio.ini`:

```bash
# Build RP2040 firmware
~/.platformio/penv/Scripts/pio run -e jumper_zero_RP2040

# Build ESP32-S3 firmware
~/.platformio/penv/Scripts/pio run -e jumper_zero_ESP32S3

# Upload RP2040 (UF2 copy to RPI-RP2 drive — board enters BOOTSEL automatically via 1200bps touch)
~/.platformio/penv/Scripts/pio run -e jumper_zero_RP2040 -t upload

# Monitor serial (RP2040 — CDC0, port auto-detected by find_JumperZ_monitor.py)
~/.platformio/penv/Scripts/pio device monitor -e jumper_zero_RP2040

# Run tests
~/.platformio/penv/Scripts/pio test -e jumper_zero_RP2040
```

> `pio` is not on PATH on this Windows machine — always use the full path `~/.platformio/penv/Scripts/pio`.

**Upload driver requirement:** The RP2040 upload uses `upload_protocol = mbed` (UF2 copy to mass-storage drive). The board's USB driver for BOOTSEL mode **must** be the default Windows USB Mass Storage driver — do **not** replace it with WinUSB via Zadig. Zadig/WinUSB is only needed for picotool, which this project does not use. If the RPI-RP2 drive stops appearing, restore the driver in Device Manager → right-click "RP2 Boot" → Update driver → Let me pick → USB Mass Storage Device.

Source files are conditionally compiled per platform using `build_src_filter` — `src/rp2040/` only builds for the RP2040 environment, `src/esp32s3/` only for ESP32-S3. Every new `src/rp2040/` subdirectory must also be added as `-I src/rp2040/<DIR>` in `platformio.ini` `build_flags`.

### PlatformIO Scripts (`scripts/`)

| Script | Status | Purpose |
|--------|--------|---------|
| `apply_patches.py` | active (pre-build) | Patches library sources before compilation |
| `extra_script.py` | active (post-build + post-upload) | UF2 output; `after_upload` hook scans for all 4 CDC ports by LOCATION suffix and prints `MONITOR_PORT`/`BRIDGE_PORT`/`OSC_FUN_PORT`/`TTL_PORT` |
| `find_JumperZ_monitor.py` | active (pre-monitor) | Auto-detects CDC 0 debug port and sets `MONITOR_PORT` |
| `find_JumperZ_upload.py` | inactive | Auto-detect upload port helper (commented out in `platformio.ini`) |

## Architecture

### RP2040 Control Flow

```
setup() → JumperZ_SEQ::JumperZ_Setup()
  ├── USB_CDC_Config::USB_CDC_setup()   # 4 CDC descriptors via TinyUSB
  ├── LedMatrix::begin(50)              # 400× WS2812B LEDs, brightness=50
  ├── rgbPatterns::startup()            # Startup animation (comet → name → sparkles)
  ├── initCH446Q()                      # PIO program load + hardware RST all 12 chips
  ├── Measurements::setup()             # Wire0 init + INA219 configuration
  ├── JsonBridge::clearFrame()
  ├── JsonBridge::begin()
  └── NanoHeader::setup()

loop() → JumperZ_SEQ::JumperZ_Loop()
  ├── Read JSON from USBSer1 (if available)
  ├── JsonBridge::handle(USBSer1, req)  # Dispatch JSON commands
  ├── JsonBridge::tick()                # Blink animation at 350ms
  ├── CurrentViz::tick()                # Current-flow animation (no-op when disabled)
  └── NanoHeader::loop()                # TTL bridge — must NOT be commented out
```

`configuration.h` is the single include that pulls in all subsystem headers. `JumperZ_SEQ.h` includes it.

### USB CDC Ports (RP2040)

4 CDC descriptors configured (`CFG_TUD_CDC=4` in `include/custom_tusb_config.h`). Most Windows setups enumerate 3 and drop CDC 3; some Windows 11 machines enumerate all 4. The `addInterface` order in `usb_cdc_config.cpp` is deliberately arranged so the most critical ports land at lower indices:

| CDC Index | Object | Name | LOCATION suffix | Function |
|-----------|--------|------|-----------------|----------|
| 0 | `Serial` | "TinyUSB" | `X.0` (or none — see below) | Default Arduino serial / debug output |
| 1 | `USBSer1` | "JZ NETSH" | `X.2` | Main JSON control channel |
| 2 | `USBSer3` | "JZ TTL" | `X.4` | Arduino Nano TTL bridge |
| 3 | `USBSer2` | "JZ Oscilloscope" | `X.6` | Dropped on most Windows; present on Win11 |

**LOCATION quirk:** On some Windows 11 systems CDC 0 (`Serial`) reports no `LOCATION` field in its USB hwid string. Both `extra_script.py` and `find_JumperZ_monitor.py` handle this with a no-location fallback — a JumperZ port with no LOCATION is treated as CDC 0.

Key constraints:
- `CFG_TUD_MSC = 0` — MSC must stay disabled; enabling it bloats the descriptor and causes Windows to drop CDC 3.
- `tud_mounted()` guard required in `NanoHeader::loop()` — CDC calls before USB enumeration completes cause Windows to drop the JZ TTL port.
- `NanoHeader::loop()` must remain active in `JumperZ_SEQ.cpp`.

### JSON Command Protocol

Commands are newline-terminated JSON sent to **USBSer1 ("JZ NETSH")**. Each command returns a JSON response on the same port.

| Command | Description |
|---------|-------------|
| `{"cmd":"ping"}` | Returns device info and LED count |
| `{"cmd":"clear"}` | Clears all LEDs + all CH446Q connections |
| `{"cmd":"wokwi_wires","wires":[...]}` | LED-only visual path render (no switching) |
| `{"cmd":"connect","nets":[{"nodes":["NANO_D3","TOP_5"],"color":"#0f0"},…]}` | Close physical CH446Q switches + light endpoints (full re-program — clears existing user nets) |
| `{"cmd":"probe_connect","nets":[{"nodes":["OSC_PROBE","TOP_5"]},…]}` | Same payload shape as `connect` but **non-destructive**: replaces only the previously-routed probe nets; existing user nets keep their LED paint and CH446Q routing. Pass empty `nets:[]` for probe-only clear. Backed by `s_probeNetIdx[16]` slot tracker in `json_bridge.cpp`. |
| `{"cmd":"netlist_query"}` | Return current path state (capped at 32 paths in JSON) |
| `{"cmd":"debug"}` | Dump chip map / paths / nets as text, then JSON ACK |
| `{"cmd":"debug","what":"summary"\|"chips"\|"paths"\|"nets"}` | Scoped debug dump |
| `{"cmd":"measure","node":"TOP_5"}` | Voltage-only: node→ISENSE_MINUS, returns bus_v = V(node) |
| `{"cmd":"measure","node":"TOP_5","plus":"5V","sensor":0}` | Current mode: plus→ISENSE_PLUS, node→ISENSE_MINUS; returns V, I, P |
| `{"cmd":"measure","node":"TOP_17","node2":"TOP_14"}` | Diff mode: node2→ISENSE_PLUS, node→ISENSE_MINUS; returns node_v, node2_v, diff_mv=V(node2)−V(node). INA219 shunt range ±320 mV. |
| `{"cmd":"measure_clear"}` | Restore full-brightness LED frame, remove measurement nets, discard snapshot |
| `{"cmd":"current_viz","enable":true,"speed":1.0}` | Enable animated current-flow sparks — direction determined automatically from node potentials (GND=0V, 3.3V, 5V seeded; propagated through net graph) |
| `{"cmd":"current_viz","enable":false}` | Disable animation and restore static frame |
| `{"cmd":"settings"}` | Get all persistent settings (`brightness`, `conn_anim`, `disconn_anim`) |
| `{"cmd":"settings","action":"set","brightness":80}` | Update one or more settings and persist to EEPROM; `brightness` applied immediately |
| `{"cmd":"settings","action":"reset"}` | Restore factory defaults to EEPROM |

Node names in `"connect"` and `"measure"` are resolved through `sfMappings[]` in `path_mapping_algo.cpp`. Any name not in that table returns an error in `"err_nodes"`.

Wire path coordinates: `["T", row, col]` (top rail 2×25), `["B", row, col]` (bottom rail 2×25), `["M1", row, col]` (mid1 5×30), `["M2", row, col]` (mid2 5×30). Wire LEDs are painted steady; endpoint LEDs blink at 350 ms.

### LED Matrix (`src/rp2040/RGB_MATRIX/`)

400 WS2812B LEDs on GPIO 25. `LedMatrix` is a **static-only class** (no instances) backed by a single `Adafruit_NeoPixel s_strip` defined once in `Led_Matrix.cpp`.

Physical LED layout (contiguous strip index):

| Section | Base | Count | Dims |
|---------|------|-------|------|
| Top rails (T) | 0 | 50 | 2 rows × 25 cols |
| Middle 1 (M1) | 50 | 150 | 5 rows × 30 cols |
| Middle 2 (M2) | 200 | 150 | 5 rows × 30 cols |
| Bottom rails (B) | 350 | 50 | 2 rows × 25 cols |

Index formulas:
- `mid1Index(row, col)  = 50  + col*5 + row`   (column-major)
- `mid2Index(row, col)  = 200 + col*5 + row`   (column-major)
- Top/bottom rails use a **snake** layout within each 5-column block.

Key API: `logicalToIndex(sec, row, col)` — maps `"T"/"B"/"M1"/"M2"` + row/col to strip index. `framePaintPathIdx()` / `frameMarkEndpointIdx()` write to the framebuffer; `frameApplyFull()` pushes it to the strip; `frameTick()` handles the 350 ms blink. `frameDimAll(factor)` scales every pixel by `factor/255` in-place (used by `measure` to dim existing connections to ~25%).

Snapshot API (used exclusively by `measure` / `measure_clear`): `frameSaveSnapshot()` / `frameRestoreSnapshot()` / `frameHasSnapshot()` / `frameClearSnapshot()` — save and restore the full-brightness frame around a measurement cycle.

### LED Patterns (`src/rp2040/RGB_MATRIX/LED_PATTERNS/`)

`rgbPatterns` namespace — called once at boot, blocks with `delay()`:
- `startup(strip)` — 4-phase sequence:
  1. Rainbow comet sweep across all 400 LEDs (~840 ms)
  2. "FABVOLT" letter-by-letter on M1 in gold (~1.1 s)
  3. "FABVOLT" breathes on M1 while "PROTOMATRIX V1" scrolls right-to-left on M2 in ice-blue (~1.3 s)
  4. Gold + ice-blue sparkle fade (~1.5 s)
- `showName(strip)` — legacy: renders "JUMPER-Z" using a 5×3 pixel font. "JUMP" on M1, "ER-Z" on M2, `START_COL=7`, `CHAR_STEP=4` cols per character. Kept for compatibility but not called by `startup()`.

### SPI Handler (`src/rp2040/SPI_HANDLER/`)

- `spi.pio.h` — **project-custom** PIO program for CH446Q multi-CS protocol. Defines `spi_ch446_multi_cs_program`, `pio_spi_ch446_multi_cs_init()`, `ch446_stb_pulse()`. Not a standard SPI program.
- `pio_spi.h/.cpp` — standard bidirectional PIO-SPI ported from Pico SDK examples.

**Naming hazard:** The Arduino-Pico core's `SoftwareSPI` library ships its own `spi.pio.h` without the CH446Q symbols. `platformio.ini` has `lib_ignore = SoftwareSPI` to prevent shadowing. Do not remove this.

### Pin Mapping (`src/rp2040/pin_map/pin_map.h`)

Logical node numbers used throughout the path-finding system:

| Range | Meaning |
|-------|---------|
| 1–30 | Top breadboard rows (TOP_1–TOP_30) |
| 31–60 | Bottom breadboard rows (BOTTOM_1–BOTTOM_30) |
| 70–93 | Arduino Nano pins (NANO_D0–NANO_D13, NANO_A0–NANO_A7, NANO_RESET, NANO_AREF) |
| 100–127 | Special function nodes (GND=100, +3.3V=103, +5V=105, DAC0=106, DAC1=107, ISENSE+=108, ISENSE−=109, ADC0–3=110–113, EMPTY_NET=127) |
| 129–169 | External 40-pin header (EXT_PIN_1–EXT_PIN_35, EXT_PIN_Tx=168, EXT_PIN_Rx=169) |

`-1` is the universal "no connection / not applicable" sentinel. `EMPTY_NET = 127`.

**Warning:** `MAIN__UART_Rx`/`MAIN_UART_Tx` labels in `pin_map.h` are **inverted** from actual function. Correct: `NANO_UART_TX = GPIO 16` (`RP_UART_TX`), `NANO_UART_RX = GPIO 17` (`RP_UART_RX`).

### CH446Q Multiplexer (`src/rp2040/CH446Q_HANDLER/`)

12× CH446Q analog crosspoint switch chips (8Y × 16X each) form the connectivity matrix:

| Chip range | Indices | Function |
|------------|---------|----------|
| A–H | 0–7 | Breadboard rows (top half A-D, bottom half E-H) |
| I–J | 8–9 | Nano header + external 40-pin header |
| K–L | 10–11 | Special function + bridge/rail |

Serial bus: **DAT** GPIO 14 | **CLK** GPIO 15 | **RST** GPIO 24 (active HIGH) | **STB_A–H** GPIO 6–13 | **STB_I–L** GPIO 20–23.

8-bit command byte (MSB first): `[ AY2 AY1 AY0 | AX3 AX2 AX1 AX0 | DS ]` — Y in upper 3 bits, X in next 4, DS=1 connect / 0 disconnect. Formula: `(y<<5)|(x<<1)|ds`.

`MUX_SWITCH` (GPIO 0) LOW routes UART to the Nano header. `ch[]` (12 entries) and `chExt[]` (2 entries for chips I/J EXT mapping) are the software mirrors of chip state.

### Arduino Nano TTL Bridge (`src/rp2040/NANO_HEADER/`)

Bridges USB CDC (JZ TTL, CDC 2) to Serial1 (GPIO 16/17) for Arduino Nano sketch upload and communication. Reset sequence via CH446Q chip J: connect X15 (GND) and X12 (NANO_RESET) to Y7 → LOW for 100 ms → open switches → HIGH. Both UART directions open immediately after RST release. Uses raw TinyUSB API (`tud_cdc_n_*` with `TTL_CDC_IDX`) for reliability.

### Path Finding (`src/rp2040/PATH_FINDING/`)

Two files form the full pipeline:

- `path_mapping_algo.h/.cpp` — global state: `net[MAX_NETS]`, `path[MAX_BRIDGES]`, `ch[12]`, `chExt[2]`, `sfMappings[]`, `nano` struct.
- `nets_to_chip_connections.h/.cpp` — 7-stage pipeline:
  1. `bridgesToPaths()` — flatten `net[].bridges[][]` into `path[]`
  2. `findStartAndEndChips()` — populate `path[i].candidates[][]`
  3. `assignPathType()` — classify `BBtoBB`, `BBtoNANO`, `BBtoSF`, `BBtoEXT`, etc.
  4. `resolveChipCandidates()` — pick least-crowded chip per node
  5. `commitPaths()` — fill `path[i].x[]/y[]` switch coordinates
  6. `resolveAltPaths()` — multi-hop routing for paths needing bridge chips
  7. `addParallelConnections()` — duplicate BB–BB paths for lower Ron

Call sequence: `netsToChipConnectionsFull()` (runs all 7 stages) → `sendAllPaths(1)`.

Special nets 0–7 are pre-defined (Empty, GND, +5V, +3.3V, DAC0, DAC1, I-Sense+/−) and never cleared. User nets start at index 8.

Reference implementation: `docs/jumperless_netlist_pathmapping_reference.md`.

### INA219 Current Measurement (`src/rp2040/MEASUREMENTS/`)

Two INA219AIDR sensors on **Wire0 (GPIO 4 SDA / GPIO 5 SCL)**. They are switched into circuit via **Chip L** on the CH446Q matrix:

| Chip L pin | Node | INA219 terminal |
|------------|------|-----------------|
| X0 | ISENSE_MINUS (109) | IN− |
| X1 | ISENSE_PLUS  (108) | IN+ |

- `Measurements::setup()` — initialises Wire0 at 400 kHz, writes config + calibration registers to both sensors.
- `Measurements::read(idx)` — returns `{shuntMv, busV, currentMa, powerMw, valid}`. Re-applies calibration on every call.
- `Measurements::scanI2C()` — scans Wire0 and prints responding addresses to `Serial`. Call once during bring-up to confirm I2C addresses, then remove from the loop.

**Configuration constants in `measurements.h`:**
- `INA219_ADDR_0 / INA219_ADDR_1` — 7-bit I2C addresses (default 0x40 / 0x41). Your hardware uses 8-bit write-address format (0x80 / 0x82) — shift right by 1 to get the 7-bit value.
- `INA219_SHUNT_OHMS` — shunt resistor value; update to match the actual component on the board. `currentMa` and `powerMw` scale from this; `shuntMv` and `busV` are always raw.

The `{"cmd":"measure"}` JSON handler (in `json_bridge.cpp`) is **non-destructive** — it preserves existing user nets. It hardware-resets the CH446Q chips, re-runs the full pipeline with the existing nets plus the new measurement nets, settles 10 ms, reads the sensor, and leaves the measurement path active.

**Two modes:**
- **Voltage-only** (no `plus` field): `node → ISENSE_MINUS`. `bus_v` = V(node).
- **Current mode** (`plus` provided): `plus → ISENSE_PLUS`, `node → ISENSE_MINUS`. Current flows plus → shunt → node; `current_ma = shunt_mv / shunt_resistance`.

**LED snapshot management:** On first `measure` call, the full-brightness framebuffer is saved (`frameSaveSnapshot`). On subsequent calls it is restored then re-dimmed (`frameDimAll(64)` → ~25%). `measure_clear` calls `frameRestoreSnapshot` + `frameClearSnapshot` to return to full brightness. Node LEDs: cyan = measured node, amber = `plus` supply side.

Node names sent via `plus` and `node` fields are **case-sensitive** and must match `sfMappings[]` exactly (always uppercase, e.g., `"5V"` not `"5v"`).

### Settings (`src/rp2040/SETTINGS/`)

`Settings` namespace — persistent board configuration stored in the RP2040's **on-chip flash** via the earlephilhower `EEPROM` emulation library. No external I2C chip required. `EEPROM.begin(64)` allocates a 64-byte region; `EEPROM.put()` writes to the RAM buffer; `EEPROM.commit()` flushes to flash.

`Settings::setup()` is the **first call** in `JumperZ_Setup()` so that `brightness` is available before `LedMatrix::begin()`. It does **not** touch Wire/I2C — `Measurements::setup()` owns Wire0 entirely.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `brightness` | uint8_t | 50 | Global LED strip brightness 0–255; passed to `LedMatrix::begin()` at boot and applied immediately on `set` |
| `conn_anim` | bool | false | Whether the USB-connect LED animation plays; also initialises `s_animEnabled` in `JumperZ_SEQ` at boot |
| `disconn_anim` | bool | false | Whether the USB-disconnect LED animation plays |
| `osc_conn_style` | uint8_t | 1 | Oscilloscope plug-in animation. `0`=off, `1`=ScopeWave, `2`=Comet, `3`=Ripple, `4`=MatrixRain. Dispatched in `JumperZ_SEQ::JumperZ_Setup()` via the `UARTMainBridge::onOscEvent` callback. |
| `osc_disconn_style` | uint8_t | 1 | Oscilloscope unplug animation. `0`=off, `1`=Flatline, `2`=RedFade, `3`=Drain. |

Layout: `Config` struct (16 bytes, starts with `SETTINGS_MAGIC`) at byte offset `0x0000` within the 64-byte EEPROM region. Must not exceed 64 bytes total.

Adding a new field: append before `_reserved[]`, shrink `_reserved` by the same byte count, and bump `SETTINGS_MAGIC` to force a one-time factory reset on next boot.

Python tool: `Research---JUMPER_Z-/PYTHON HACKS/LED FETCHING/settings_tool.py` — interactive menu + CLI flags (`--get`, `--set KEY=VALUE`, `--reset`).

### Current Visualization (`src/rp2040/MEASUREMENTS/current_viz.h/.cpp`)

`CurrentViz` namespace — animates a comet spark along each active net's bridge connections, flowing from high to low potential:

- Voltage seeding: GND (node 100) = 0 V, 3.3V (node 103) = 3.3 V, 5V (node 105) = 5.0 V. Propagated through the net graph; direction determined via `s_from[]` (propagation source) rather than voltage difference (all nodes in a net settle to the same potential).
- Bridges where direction is unknown (isolated from all supplies, or equal potentials) are **skipped entirely** — no bidirectional fallback.
- Only breadboard nodes (TOP_1–30, BOTTOM_1–30) have LED positions; non-LED nodes (GND, 5V, NANO, etc.) participate in voltage propagation only.
- The comet follows the **actual painted pixels** in the framebuffer (`frameIsLit`), not a hardcoded row:
  - Same-section (TOP↔TOP or BOTTOM↔BOTTOM): `buildSameSectionPath` counts lit pixels per row across the full column span; the row with the most lit pixels is the wire body row.
  - Cross-section (TOP↔BOTTOM): `buildCrossPath` walks all candidate pixels in paint order and keeps only those confirmed lit by `frameIsLit`.

API:
- `CurrentViz::enable(bool on, float speed)` — enable/disable; `speed=1.0` → ~750 ms full cycle.
- `CurrentViz::tick()` — call every loop iteration; rate-limited to ~33 fps; no-op when disabled.
- `CurrentViz::isEnabled()` — query state.

Controlled via `{"cmd":"current_viz","enable":true/false,"speed":N}` JSON command.

### Debug Module (`src/rp2040/DEBUG/`)

`JZDebug` namespace — triggered on demand via JSON or direct call:

```cpp
JZDebug::printAll();           // chip summary + paths + nets + crosspoint grid
JZDebug::printChipSummary();   // one line per chip: active X/Y pins
JZDebug::printChipMap();       // full X×Y crosspoint grid with node labels
JZDebug::printPaths();         // all path[] entries with hops
JZDebug::printNets();          // all configured nets
```

All functions accept a `Stream&` (default `Serial`). The `{"cmd":"debug"}` JSON handler sends output back to the caller (USBSer1) so Python can read it directly. Use the Python tool `debug_menu.py` for interactive access.

### UART Bridge (RP2040 ↔ ESP32-S3 ↔ STM32)

Fully transparent byte pipe between **USBSer2** (CDC 3, "JZ Oscilloscope" → `OSC_FUN_PORT` on the host) and the STM32 USART. No PING/PONG, no line framing — every byte is forwarded verbatim in both directions.

```
PC ─USB─► RP2040 USBSer2 ─PIO UART─► ESP32 UART0 ─► ESP32 UART1 ─► STM32 RX
PC ◄─USB─ RP2040 USBSer2 ◄─PIO UART─ ESP32 UART0 ◄─ ESP32 UART1 ◄─ STM32 TX
```

| Hop | Wires |
|-----|-------|
| RP2040 ↔ ESP32-S3 (UART0) | RP GPIO 19 (TX) → ESP GPIO 44 (RX), RP GPIO 18 (RX) ← ESP GPIO 43 (TX). RP2040 side uses `SerialPIO` so Serial1 stays free for the Nano TTL bridge. |
| ESP32-S3 (UART1) ↔ STM32 | ESP GPIO 46 (TX) → STM32 RX, ESP GPIO 45 (RX) ← STM32 TX. Pins also wired to Chip K crosspoints X4/X5. |

Baud is 115200 8N1 throughout — adjust `STM_UART_BAUD` in `src/esp32s3/UART_BRIDGE/rp_stm_bridge.h` and the Python `--baud` flag together if the STM32 firmware uses a different rate.

JSON helper on USBSer1: `{"cmd":"stm_cmd","data":"#A#"}` injects `data + '\n'` into the pipe. STM32 replies always come back on USBSer2 (`OSC_FUN_PORT`) — never USBSer1.

Python helpers (in `Research---JUMPER_Z-/PYTHON HACKS/LED FETCHING/`):
- `osc_bridge.py` — generic `--watch` / `--send` / `--interactive` byte-pipe CLI.
- `osc_stream.py` — focused trigger-and-stream helper; default trigger is `#A#`.

### Oscilloscope Module Hot-Plug Detection (`src/esp32s3/UART_BRIDGE/osc_detect.cpp`)

The oscilloscope module mates via magnetic pogo pins that carry both power and the STM32 USART. `OscDetect` on the ESP32 uses the STM32 TX line itself as a presence signal:

- An internal pulldown is set on **GPIO 45** (STM_UART_RX_PIN) via `gpio_set_pull_mode(GPIO_PULLDOWN_ONLY)`. This does not interfere with the UART1 routing — the STM32's push-pull TX easily drives the line HIGH at 115200 baud.
- Sampled at ~200 Hz: any HIGH within the last **200 ms** → `CONNECTED`; only LOW for 200 ms → `DISCONNECTED`.
- On state change, ESP32 injects a 5-byte sentinel into the UART0 stream toward the RP2040: `FE FD FE FD 01` (connected) or `FE FD FE FD 02` (disconnected). **No probe bytes are ever sent to the STM32** — detection is fully passive.
- The RP2040 sniffs the ESP→USBSer2 path in `uart_main_bridge.cpp` and swallows the sentinel before it reaches Python. Real STM32 data starting with `FE FD FE FD <non-event>` is held briefly and forwarded intact.
- On a connect/disconnect event the sniffer fires `UARTMainBridge::onOscEvent()`, which is wired in `JumperZ_SEQ.cpp` to play `rgbPatterns::oscConnected()` (green sine-wave sweep across M1+M2, ~800 ms) or `rgbPatterns::oscDisconnected()` (amber flat-line on row 2, ~400 ms).

**Tradeoffs:**
- The sentinel uses a 5-byte magic prefix; a binary STM32 stream could in theory contain `FE FD FE FD <01|02>` and trigger a false LED animation (~1 in 2^40 for random bytes — practically negligible).
- LED patterns are blocking (~800 ms on connect). USBSer2 ↔ STM32 traffic pauses for that window. Acceptable since the STM32 has just (re)booted via the pogo pins and isn't streaming yet.

## Python Host Tools (`Research---JUMPER_Z-/PYTHON HACKS/LED FETCHING/`)

These run on the PC and communicate with the board over USB serial.

| File | Purpose |
|------|---------|
| `main.py` | Fetch Wokwi diagram, build wire paths, send to board |
| `measure.py` | CLI tool for INA219 measurement. Modes: continuous (`-n`), `--guided` (two-pass baseline/load corrected current), `--autodiff` (auto-cluster HIGH/LOW for toggling signals). `--samples N` controls sample count for autodiff. |
| `current_viz.py` | Current-flow LED animation. Default (no flags): auto-detect all flows from netlist and start. `--on`/`--off` enable/disable without display. `--select` interactive segment picker. `--interactive` toggle menu. `--speed N` multiplier. Imports `BoardConn` from `measure.py`. |
| `debug_menu.py` | Interactive terminal menu for `{"cmd":"debug"}` requests |
| `bridge_send.py` | Low-level send helpers: `send_wokwi_wires()`, `send_connect_netlist()`, `send_connect_then_wires()` |
| `netlist.py` | `build_nets()`, `build_jz_nets()` — group Wokwi connections into nets |
| `format_out.py` | `connections_to_logical_wires()` — convert Wokwi connections to logical wire paths for the board |
| `wire_path.py` | `expand_manhattan()` — L-path expansion for same-section wires |
| `logical_map.py` | `wokwi_node_to_logical()` — Wokwi node string → `[section, row, col]` |
| `led_map.py` | `wokwi_node_to_led()` — Wokwi node → LED strip index |
| `led_diagnostic.py` | Physical LED layout verification tool (interactive, board must be connected) |
| `wokwi_fetch.py` | Fetch `diagram.json` from a Wokwi project URL |
| `OSC_FUN_MEASUREMENTS/probe_connect.py` | Route oscilloscope probes & function-generator outputs (Chip K X8–X13) to any board node. Flags: `--master`, `--3v3`, `--5v`, `--square`, `--sine`, `--ext-gnd NODE`, `--no-ext-gnd`, `--extra NODE NODE [NODE …]` (repeatable), `--clear` (probe-only clear), `--clear-all` (full board wipe), `--list`. By default the ext-GND clip is auto-tied to GND. Uses the **non-destructive** `probe_connect` JSON command — main.py / `connect` paths are preserved through probe routing changes. |

Board auto-detection uses VID `1D51` / PID `ACAB`. Bridge port = USB location suffix `X.2` (USBSer1). Debug port = suffix `X.0` (Serial) — or no LOCATION at all on some Windows 11 machines. Cross-section wires (rail↔M1/M2) show endpoints only — no intermediate path. Same-section wires (M1↔M1, M2↔M2) use full Manhattan L-path.

### Chip K Probe Pins (oscilloscope + function generator)

The CH446Q Chip K crosspoint exposes 6 dedicated probe pins:

| Chip K X | Node # | Primary name | Friendly aliases | Purpose |
|----------|--------|---------------|------------------|---------|
| X8 | 161 | `OSC_PROBE` | `MASTER_PROBE` | Master scope probe |
| X9 | 162 | `EXT_GND` | `EXTERNAL_GND` | External GND clip |
| X10 | 163 | `SQUARE_WAVE_FUN` | `SQUARE_WAVE` | Function-gen square output |
| X11 | 164 | `SINE_TRANG_FUN` | `SINE_WAVE`, `TRIANGLE_WAVE` | Function-gen sine/triangle |
| X12 | 165 | `EXTRA_1` | `PROBE_3V3`, `PROBE_3.3V` | 3.3V-range scope probe |
| X13 | 166 | `EXTRA_2` | `PROBE_5V` | 5V-range scope probe |

All names live in `sfMappings[]` in `path_mapping_algo.cpp` and are accepted by the `connect` and `measure*` JSON commands. **Historical bug fixed:** `SQUARE_WAVE_FUN` was previously mis-mapped to node 162 (collided with `EXT_GND`); `EXT_GND` was missing from `sfMappings[]` entirely. Both fixed and aliases added.

## Custom Board Definitions

Custom board JSON files in `boards/`:
- `jumper_z_rp2040.json` — VID `0x1D51`, PID `0xACAB`, 2MB flash, 262KB RAM. Upload protocol set to `"mbed"` (UF2 mass-storage copy). Do not change to `"picotool"` — it requires a different USB driver that breaks mass-storage upload.
- `jumper_z_esp32s3.json` — VID `0x303A`, PID `0x1001`, 8MB flash QIO

Variant pin definitions in `Variants/RP2040_VARIANT/` and `Variants/ESP32S3_VARIANT/`.

## Libraries

- **Adafruit NeoPixel** — WS2812B LED strip control
- **Adafruit TinyUSB Library** — Multi-CDC USB serial
- **ArduinoJson** — JSON command parsing/serialization
- **Wire** (built-in) — I2C for INA219 sensors on GPIO 4/5
- `lib_ignore = SoftwareSPI` — prevents shadowing of the project's custom `spi.pio.h`
