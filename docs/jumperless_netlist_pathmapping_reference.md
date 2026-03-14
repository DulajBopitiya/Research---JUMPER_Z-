# Jumperless Rev3.1 — Netlist & Path Mapping Algorithm Reference

> Source: JumperlessNano/src (Jumperless breadboard firmware rev3.1)
> Purpose: Reference for implementing JumperZ path mapping

---

## 1. Netlist Data Structure (`netStruct`)

Defined in `MatrixStateRP2040.h`:

```c
struct netStruct {
  uint8_t number;                    // Net identifier (0 = empty)
  const char *name;                  // e.g. "Net 3"
  int8_t nodes[MAX_NODES];           // Connected nodes (0-terminated, max 64)
  int8_t bridges[MAX_NODES][2];      // Pairs of connected nodes
  int8_t specialFunction;            // -1 = regular, or special function ID
  uint8_t intersections[8];          // Other nets sharing nodes
  int8_t doNotIntersectNodes[8];     // Nodes that cannot share this net
  uint8_t priority;                  // Path preference 0-3 (unused currently)
  rgbColor color;                    // RGB display color
  uint32_t rawColor;                 // Raw hex color
  char *colorName;                   // Color name string
  bool machine;                      // true = machine-generated, false = user
  int duplicatePaths[MAX_DUPLICATE]; // Parallel path indices for redundancy
  int numberOfDuplicates;            // Count of duplicate paths
};
```

### Pre-defined Special Nets

| Net # | Name           | Cannot Intersect With      |
|-------|----------------|---------------------------|
| 0     | Empty          | —                         |
| 1     | GND            | 5V, 3.3V, DAC0, DAC1      |
| 2     | +5V            | GND, DAC0, DAC1            |
| 3     | +3.3V          | GND, DAC0, DAC1            |
| 4     | DAC 0          | GND, 5V, 3.3V, DAC1       |
| 5     | DAC 1          | GND, 5V, 3.3V, DAC0       |
| 6     | Current Sense+ | Current Sense−             |
| 7     | Current Sense− | Current Sense+             |

### Node Number Ranges

| Range  | Meaning                                 |
|--------|-----------------------------------------|
| 1–30   | Top breadboard rows (TOP_1 – TOP_30)    |
| 31–60  | Bottom breadboard rows (BOT_1 – BOT_30) |
| 70–93  | Arduino Nano pins (D0–D13, A0–A7, etc.) |
| 100–127| Special function nodes (GND, 5V, DACs, ADCs, GPIO) |

Nodes stored left-justified in `nodes[]`, terminated by 0.

---

## 2. Path Mapping Algorithm (`NetsToChipConnections.cpp`)

Eight sequential stages translate logical bridges → physical CH446Q switch coordinates.

### Stage 1: `bridgesToPaths()`
- Copies `netStruct.bridges[]` into a flat `pathStruct` array
- Each path entry holds: net number, start node, end node, chip hops (up to 4)

### Stage 2: `findStartAndEndChips()`
- Maps each node to candidate CH446Q chips using lookup tables:
  - Breadboard nodes → `bbNodesToChip[]` (static, one chip per node)
  - Nano pins → `nano.mapIJ[]` / `nano.mapKL[]` (1–2 candidate chips)
  - Special function nodes → searched across SF chips I, J, K, L

### Stage 3: `mergeOverlappingCandidates()`
- For paths where both nodes have multiple chip candidates:
  - Finds overlap (both can reach same chip) → assigns to that chip
  - No overlap → sets `altPathNeeded = true` for multi-hop routing later

### Stage 4: `assignPathType()`
Classifies each path. Node order is standardized (BB → NANO → SF):

| Type        | Description                              |
|-------------|------------------------------------------|
| BBtoBB      | Breadboard ↔ Breadboard (chips A–H)      |
| BBtoNANO    | Breadboard ↔ Arduino Nano                |
| BBtoSF      | Breadboard ↔ Special Function            |
| NANOtoNANO  | Nano ↔ Nano (SF chips I, J, K, L)        |
| NANOtoSF    | Nano ↔ Special Function                  |
| SFtoSF      | Special Function ↔ Special Function      |
| *L variants | Same as above but routing via Chip L     |

### Stage 5: `resolveChipCandidates()`
- For paths still with unresolved candidate chips:
  - `sortAllChipsLeastToMostCrowded()` ranks chips by active connections
  - Greedy: picks least-crowded candidate chip (`moreAvailableChip()`)

### Stage 6: `commitPaths()`
Allocates physical X/Y coordinates per path type:

**BBtoBB:**
- Uses "lanes" (lane 0 / lane 1) — pairs of crossover connections
- `xMapForChipLane0()` / `xMapForChipLane1()` for X coordinates
- `yMapForNode()` for Y coordinates
- Prefers stacking on a lane already used by same net

**BBtoSF / NANOtoSF:**
- Direct SF connection via `xMapForNode()` + `yMapForNode()`
- If Chip L involved: special bridge routing through Chip L

**NANOtoNANO:**
- Same SF chip: X coordinates only (Y = -2, not allocated)
- Different SF chips: sets `altPathNeeded` flag

### Stage 7: `resolveAltPaths()` / `resolveUncommittedHops()`
- Handles paths where direct single-chip connection is impossible
- Builds multi-hop routes through intermediate chips
- Allocates additional X/Y hops (path can span up to 4 chip hops)

### Stage 8: `sendAllPaths()`
- Iterates committed paths, calls `sendPath(i, setOrClear)`
- Transmits each hop's X/Y coordinates to CH446Q via SPI

---

## 3. CH446Q Crosspoint Switch Abstraction

### Hardware Layout (12 chips)

| Chips    | Role                                        |
|----------|---------------------------------------------|
| A–H (0–7)| Breadboard connectivity matrix              |
| I–J (8–9)| Arduino Nano pin connectivity               |
| K–L (10–11)| Special function + Nano bridge            |

Each chip: 16 X lines × 8 Y lines. Any X can connect to any Y.

### `chipStatus` Struct

```c
struct chipStatus {
  int chipNumber;       // 0-11
  char chipChar;        // 'A'-'L'
  int8_t xStatus[16];  // Net on each X line (-1 = unused)
  int8_t yStatus[8];   // Net on each Y line
  const int8_t xMap[16]; // X pin → logical node
  const int8_t yMap[8];  // Y pin → logical node
};
```

### `pathStruct`

```c
struct pathStruct {
  int8_t net;
  int8_t node[2];          // Start/end logical nodes
  int8_t chip[4];          // Chip hops (up to 4, -1 = unused)
  int8_t x[4];             // X coordinate per hop
  int8_t y[4];             // Y coordinate per hop (-2 = N/A)
  int8_t candidates[2][3]; // Candidate chips per node
  bool altPathNeeded;
  int8_t pathType;
};
```

### SPI Control

- **DAT:** GPIO 14 | **CK:** GPIO 15
- **CS per chip:** GPIOs 6–13, 20–23
- PIO-based SPI (time-critical functions)

Key functions:

| Function | Description |
|----------|-------------|
| `initCH446Q()` | Init PIO-SPI, reset all chips |
| `sendXYraw(chip, x, y, set)` | Transmit single X/Y switch command |
| `sendPath(i, set)` | Send all hops for path[i] |
| `sendAllPaths()` | Batch send all active paths |
| `clearAllConnectionsOnChip()` | Disconnect all nets on a chip |

---

## 4. Logical → Physical Translation Example

```
Request:    Connect NANO_D0 ↔ GND

Step 1:     Add bridge to GND net (net 1)
Step 2:     NANO_D0 → candidates: {Chip I, Chip J}
            GND     → hardcoded: Chip L
Step 3:     No overlap → altPathNeeded = true
Step 4:     Path type: NANOtoSF
Step 5:     Pick least-crowded: Chip I
Step 6:     Chip I: x = xMapForNode(NANO_D0, CHIP_I), y = -2
            Chip L: x = xMapForNode(GND, CHIP_L), y = yMapForNode(GND, CHIP_L)
Step 7:     Multi-hop: Chip I → (L's Y row for I) → Chip L
Step 8:     sendXYraw(CHIP_I, x, y, SET)
            sendXYraw(CHIP_L, x, y, SET)
```

---

## 5. Key Files in JumperlessNano/src

| File | Purpose |
|------|---------|
| `MatrixStateRP2040.h/.cpp` | All struct definitions + init tables (netStruct, chipStatus, pathStruct) |
| `NetManager.h/.cpp` | Netlist CRUD — create/merge/delete nets, manage bridges |
| `NetsToChipConnections.h/.cpp` | Full path mapping algorithm (all 8 stages) |
| `CH446Q.h/.cpp` | Hardware SPI abstraction for CH446Q chips |
| `JumperlessDefinesRP2040.h` | Constants: MAX_NETS=64, MAX_BRIDGES=255, node ranges |

---

## 6. Key Design Rules for JumperZ Adaptation

1. **Do Not Intersect (DNI)**: Power rails cannot share nets — enforced in `checkDoNotIntersectsByNet()` and `checkDoNotIntersectsByNode()`
2. **Duplicate paths for power**: Priority nets get up to 12 parallel paths for lower resistance (`duplicateSFnets()`)
3. **Lane stacking**: BBtoBB paths prefer reusing an existing net's lane to avoid collision
4. **Chip L is the bridge**: Special function connections always route through Chip L
5. **Least-crowded chip selection**: Greedy assignment keeps connections balanced across chips
6. **Multi-hop limit**: Paths span at most 4 chip hops (chip[0..3], x[0..3], y[0..3])
