# JumperZ Python Tools — Context Reference

This file is a working reference for Claude (and the developer) when editing
scripts in this directory.  Keep it up to date as the codebase changes.

---

## Board connection

**USB IDs:** VID `1D51` / PID `ACAB`

| CDC port | LOCATION suffix | Object | Purpose |
|----------|----------------|--------|---------|
| CDC 0 | `X.0` (or no LOCATION) | `Serial` | Debug output |
| CDC 1 | `X.2` | `USBSer1` | **JSON control — use this** |
| CDC 2 | `X.4` | `USBSer3` | Arduino Nano TTL bridge |
| CDC 3 | `X.6` | `USBSer2` | Oscilloscope (often absent on Windows) |

Auto-detection is in `bridge_send.py → find_ports()`.  Returns `(debug_port, bridge_port)`.

`BoardConn` (in `measure.py`) wraps the bridge port with `.send(dict) → dict`.
All commands are newline-terminated JSON sent to CDC 1; board replies one JSON line.

---

## JSON commands (send to CDC 1 / JZ NETSH)

```jsonc
{"cmd":"ping"}
{"cmd":"clear"}
{"cmd":"connect","nets":[{"nodes":["5V","TOP_5","TOP_10"],"color":"#0f0"}]}
{"cmd":"wokwi_wires","wires":[...]}
{"cmd":"netlist_query"}                         // returns path[] with n1,n2 node numbers
{"cmd":"debug"}                                 // full chip/path/net dump as text + JSON ACK
{"cmd":"debug","what":"summary"|"chips"|"paths"|"nets"}
{"cmd":"measure","node":"TOP_5"}
{"cmd":"measure","node":"TOP_5","plus":"5V","sensor":0}
{"cmd":"measure_diff","node":"TOP_17","node2":"TOP_14","sensor":0}  // two-pass bus-V, 0–32V range
{"cmd":"measure_clear"}
{"cmd":"current_viz","enable":true,"speed":1.0}
{"cmd":"current_viz","enable":false}
// Segment filter (node numbers from netlist_query n1/n2 fields):
{"cmd":"current_viz","enable":true,"speed":1.0,"bridges":[[105,5],[10,100]]}
// LED framebuffer dump — returns LED_DUMP_BEGIN/END block with PATH/ENDP/EP hex lines:
{"cmd":"led_dump"}
// ESP32-S3 ↔ STM32 UART bridge:
{"cmd":"uart_ping"}                             // expects [ESP32] PONG on debug port
{"cmd":"stm_cmd","data":"#A#"}                  // forward DATA to STM32; replies arrive as {"type":"stm_data","data":"..."}
// Persistent EEPROM settings (CAT24C256WI-G, I2C 0x50, SDA=GPIO4 SCL=GPIO5):
{"cmd":"settings","action":"get"}
{"cmd":"settings","action":"set","brightness":80,"conn_anim":true,"disconn_anim":false}
{"cmd":"settings","action":"reset"}
{"cmd":"settings","action":"verify"}            // returns {"match":true/false,"eeprom_ok":true/false}
```

Node names in `connect` / `measure` are **case-sensitive** and must be uppercase
(e.g. `"5V"`, `"GND"`, `"TOP_5"`).

---

## Node number ↔ name mapping

See `node_map.py` — import `name(n)` / `num(name)` / `is_supply(n)` / `is_breadboard(n)`.

Quick lookup:

| Range | Names | Node numbers |
|-------|-------|-------------|
| Top breadboard | TOP_1 – TOP_30 | 1 – 30 |
| Bottom breadboard | BOTTOM_1 – BOTTOM_30 | 31 – 60 |
| Nano header | NANO_D0 – NANO_A7 | 70 – 93 |
| GND | GND | 100 |
| 3.3 V rail | 3V3 | 103 |
| 5 V rail | 5V | 105 |
| DAC outputs | DAC0 / DAC1 | 106 / 107 |
| Current sense | ISENSE+ / ISENSE- | 108 / 109 |
| ADC inputs | ADC0 – ADC3 | 110 – 113 |
| External 40-pin | EXT_1 – EXT_35 | 129 – 163 |
| Ext UART | EXT_Tx / EXT_Rx | 168 / 169 |

---

## Script inventory

| File | What it does |
|------|-------------|
| `bridge_send.py` | Low-level: `find_ports()`, `send_json_line()`, `send_wokwi_wires()`, `send_connect_netlist()`, `send_connect_then_wires()` |
| `measure.py` | `BoardConn` class; voltage/current measurement CLI; `--guided`, `--autodiff`, `--node2` (diff via `measure_diff`), `-c` continuous, `-i` interactive |
| `current_viz.py` | Current-flow LED animation; default `--auto` mode (queries netlist, classifies direct/propagated flows); `--on/--off/--select/--interactive` modes |
| `node_map.py` | `NODE_NAME` / `NODE_NUM` dicts; `name()`, `num()`, `is_supply()`, `is_breadboard()` |
| `main.py` | Fetch Wokwi diagram → build wire paths → send to board |
| `debug_menu.py` | Interactive menu for `{"cmd":"debug"}` requests |
| `netlist.py` | `build_nets()`, `build_jz_nets()` — group Wokwi connections into nets |
| `format_out.py` | `connections_to_logical_wires()`; `_expand_cross_m1_m2()` for M1↔M2 cross-section routing; Wokwi routing-hint support (`"v"`/`"h"` hint → `"vh"`/`"hv"` order) |
| `wire_path.py` | `expand_manhattan()` — L-path expansion for same-section wires; `expand_logical_path()` — T↔M1 / M2↔B cross-section paths (fills all intermediate rows at junction column) |
| `logical_map.py` | `wokwi_node_to_logical()` — Wokwi node string → `[section, row, col]` |
| `led_map.py` | `wokwi_node_to_led()` — Wokwi node → LED strip index |
| `led_diagnostic.py` | Physical LED layout verification (interactive, board must be connected) |
| `led_debug.py` | LED matrix debug viewer; fetches framebuffer via `{"cmd":"led_dump"}`; renders ANSI-coloured map (PATH layer + ENDP endpoints) in terminal; `--loop` for continuous refresh |
| `esp32_bridge_test.py` | Test RP2040 ↔ ESP32-S3 ↔ STM32 UART bridge; modes: `uart_ping` (default), `--stm DATA` (forward to STM32), `--watch` (passive monitor); colours debug output by source ([ESP32]=green, [STM32]=cyan) |
| `settings_tool.py` | Persistent EEPROM settings manager; reads/writes `brightness`, `conn_anim`, `disconn_anim` to CAT24C256WI-G (I2C 0x50); `--get/--set/--verify/--reset` or interactive menu |
| `wokwi_fetch.py` | Fetch `diagram.json` from a Wokwi project URL |
| `MEASURE_CALCULATIONS/capacitance.py` | Capacitance calculation helpers |
| `MEASURE_CALCULATIONS/resistance.py` | Resistance calculation helpers |
| `MEASURE_CALCULATIONS/vi_graph.py` | V-I graph utilities |

---

## current_viz modes

**Default (`--auto` or no flag):**  
`auto_viz()` calls `netlist_query`, classifies each bridge:
- **direct** — one endpoint is a supply/GND node; direction is deterministic
- **prop** — both endpoints are breadboard nodes; firmware propagates voltage to determine direction

Prints a table of flows, then sends `current_viz enable=true` (no filter). Waits until Ctrl-C, then disables.

**Other modes:** `--on` (enable, no display), `--off` (disable), `--select` (interactive bridge picker), `--interactive` (toggle + speed menu, +/- keys, `s` to select segments).

---

## current_viz segment-filter protocol

The firmware (`current_viz.cpp`) animates comets only on bridges where current
direction can be determined from `s_from[]` (propagation-source tracking):
- Positive supply (5V/3V3/DAC0/DAC1): current flows **away** from supply node
- GND: current flows **toward** GND node
- Bridges not reachable from any supply are skipped (no animation)
- Bridges with unknown direction are skipped (no bidirectional fallback)

**Wire path followed by comets (mirrors paintBridgeLeds exactly):**
- `TOP ↔ TOP` (M1→M1): along M1 row 0, column-major step = 5
- `BOTTOM ↔ BOTTOM` (M2→M2): along M2 row 0, column-major step = 5
- `TOP → BOTTOM` cross-section:
  `M1(0,cTop)` → `M1(3,cTop)` → `M1(4,cTop)` → `M2(0,cTop)` → `M2(1,cTop..cBot)` → `M2(0,cBot)`
  (rows 1 and 2 of M1 are unpainted — skipped to avoid lighting dark LEDs)
- `BOTTOM → TOP`: mirror of the above

**Filter:** `"bridges":[[n1,n2],...]` — uses raw node numbers from `netlist_query`.
Absent or empty `"bridges"` key → no filter (animate all reachable bridges).
Filter matching is bidirectional: `(n1,n2)` matches both stored orders.

**Python helper** (`current_viz.py → segment_select()`):
1. Calls `{"cmd":"netlist_query"}` → deduplicate paths by `(min,max)` node pair
2. Displays menu with human-readable names (via `node_map.name()`)
3. User picks by number, "A" for all, "Q" to disable
4. Sends `{"cmd":"current_viz","enable":true,"bridges":[[n1,n2],...]}` with selected pairs

---

## LED matrix layout (400 LEDs total)

| Section | Strip base | Count | Indexing |
|---------|-----------|-------|---------|
| Top rails (T) | 0 | 50 | snake within 5-col blocks |
| Middle 1 (M1) | 50 | 150 | column-major: `50 + col*5 + row` |
| Middle 2 (M2) | 200 | 150 | column-major: `200 + col*5 + row` |
| Bottom rails (B) | 350 | 50 | snake within 5-col blocks |

M1 = TOP rows (breadboard top half), M2 = BOTTOM rows (breadboard bottom half).
`TOP_N` maps to M1 column `N-1` (0-indexed).
`BOTTOM_N` maps to M2 column `N-1` (0-indexed).

---

## measure.py modes

| CLI flag | Firmware command | Notes |
|----------|-----------------|-------|
| `python measure.py TOP_5` | `measure` | Single voltage reading |
| `python measure.py TOP_5 -c` | `measure` (loop) | Continuous until Ctrl+C |
| `python measure.py TOP_5 --plus 5V` | `measure` (current mode) | Shunt current via INA219 |
| `python measure.py TOP_5 --node2 TOP_10` | `measure_diff` | Two-pass bus-V diff, 0–32V range |
| `python measure.py TOP_5 --guided` | `measure` (2-pass) | Baseline → load → net current |
| `python measure.py TOP_5 --autodiff` | `measure` (N samples) | Cluster HIGH/LOW states |
| `python measure.py -i` | interactive | REPL with `loop`, `diff`, `guided`, `autodiff` |
| `python measure.py --clear` | `measure_clear` | Restore netlist LED brightness |

---

## settings_tool.py — persistent EEPROM settings

EEPROM: CAT24C256WI-G, I2C address `0x50`, SDA=GPIO4, SCL=GPIO5.

| Setting | Type | Default | Notes |
|---------|------|---------|-------|
| `brightness` | int 0–255 | 50 | LED strip global brightness |
| `conn_anim` | bool | false | Play animation on USB connect |
| `disconn_anim` | bool | false | Play animation on USB disconnect |

```bash
python settings_tool.py                       # interactive menu
python settings_tool.py --get                 # print settings + eeprom_ok status
python settings_tool.py --set brightness=80 conn_anim=true
python settings_tool.py --verify              # check EEPROM matches RAM
python settings_tool.py --reset               # restore factory defaults
```

Response keys: `ok`, `brightness`, `conn_anim`, `disconn_anim`, `eeprom_ok`, `save_ok`.

---

## led_debug.py — framebuffer viewer

Sends `{"cmd":"led_dump"}` and renders the 400-LED framebuffer as an ANSI map.
Board responds with a `LED_DUMP_BEGIN` / `LED_DUMP_END` block containing:
- `PATH:RRGGBB...` — path layer colours (hex, 400×6 chars)
- `ENDP:RRGGBB...` — endpoint layer colours
- `EP:0101...`     — endpoint flags (400 chars of '0'/'1')

```bash
python led_debug.py                     # single snapshot
python led_debug.py --loop              # refresh every 1 s
python led_debug.py --loop --interval 0.5
python led_debug.py --raw               # print raw hex lines (for sharing/debugging)
```

---

## esp32_bridge_test.py — UART bridge diagnostics

Tests the RP2040 ↔ ESP32-S3 ↔ STM32 UART chain.

```bash
python esp32_bridge_test.py                 # uart_ping → look for [ESP32] PONG on debug port
python esp32_bridge_test.py --stm "#A#"     # forward raw data to STM32, stream replies
python esp32_bridge_test.py --stm "#A#" --once  # send once, collect 3 s of stm_data, exit
python esp32_bridge_test.py --watch         # passive monitor only
```

Debug output is colour-coded: `[ESP32]` lines in green, `[STM32]` lines in cyan.
STM32 replies arrive as `{"type":"stm_data","data":"..."}` JSON on CDC 1 (magenta in terminal).

---

## wire_path.py — path expansion

| Function | Input | Output |
|----------|-------|--------|
| `expand_manhattan(a, b, order="vh")` | Two bb-hole node strings (same section) | List of bb-hole nodes along L-path |
| `expand_logical_path(a_log, b_log)` | Two `[section, row, col]` points | List of logical points for T↔M1 or M2↔B cross-section paths |

`expand_logical_path` fills all intermediate rows at the junction column (no visual gaps):
- `T → M1`: drop M1 rows 0..r_b at c_a, then go horizontal
- `M1 → T`: go horizontal at r_a to c_b, then rise M1 rows r_a..0, then rail
- `M2 → B` and `B → M2`: mirrors of the above for the bottom half

`format_out.py → _expand_cross_m1_m2()` handles M1↔M2 cross-section, using the **source** endpoint's column as the crossing column.

---

## Typical workflow

```python
# 1. Connect a circuit (closes CH446Q switches + lights LEDs)
from bridge_send import send_connect_netlist
send_connect_netlist([
    {"nodes": ["5V", "TOP_5", "TOP_10"], "color": "#f80"},
    {"nodes": ["BOTTOM_3", "GND"],       "color": "#08f"},
])

# 2. Enable current-flow animation (all bridges)
from measure import BoardConn
conn = BoardConn()
conn.send({"cmd": "current_viz", "enable": True, "speed": 1.0})

# 3. Auto-detect flows and animate (CLI)
#    python current_viz.py           # --auto is the default

# 4. Interactive segment selection
#    python current_viz.py --select

# 5. Measure voltage at a node
conn.send({"cmd": "measure", "node": "TOP_10"})

# 6. Differential voltage (two-pass, no ±320mV limit)
conn.send({"cmd": "measure_diff", "node": "TOP_17", "node2": "TOP_14"})

# 7. Adjust LED brightness persistently
#    python settings_tool.py --set brightness=120

# 8. Inspect live LED framebuffer
#    python led_debug.py --loop

# 9. Clear everything
conn.send({"cmd": "clear"})
conn.close()
```
