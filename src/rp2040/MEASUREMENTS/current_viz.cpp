#include "current_viz.h"
#include "path_mapping_algo.h"   // net[], MAX_NETS, MAX_NODES
#include "Led_Matrix.h"
#include "pin_map.h"

// Current direction is determined by propagating known supply voltages:
//   GND (100)=0V, 3.3V (103)=3.3V, 5V (105)=5.0V
//
// A bridge is animated only when BOTH endpoints have a known voltage AND they
// differ by more than 50 mV.  Bridges with unknown or equal potentials are
// skipped entirely — no bidirectional fallback.
//
// The comet travels along the actual painted wire path:
//   • Same-section (TOP↔TOP or BOTTOM↔BOTTOM): along row 0 of M1/M2 (step=5)
//   • Cross-section (TOP↔BOTTOM): down M1 column → across M2 row 1 → M2 row 0

namespace CurrentViz
{

// ── State ──────────────────────────────────────────────────────────────────

static bool     s_enabled  = false;
static float    s_speed    = 1.0f;
static uint32_t s_lastTick = 0;
static float    s_phase[MAX_NETS];  // 0.0 – 1.0, per net, advances each tick

// Per-node computed voltages.  -1.0 = unknown.
// Node numbers run 1–169; index 0 unused.
static float    s_volt[170];

// Propagation source: s_from[n] = node that propagated voltage into node n.
// Supply seeds (GND=100, 3V3=103, 5V=105) keep s_from=-1 (they were not
// propagated into, they are the origin).
// Used to determine current direction within equal-potential nets.
static int      s_from[170];

// Bridge-pair filter.  When s_filterCount > 0, only bridges whose (n1,n2)
// pair (bidirectional) appears in s_filterPairs are drawn.
static constexpr int MAX_FILTER_PAIRS = 32;
static int16_t  s_filterPairs[MAX_FILTER_PAIRS][2];
static int      s_filterCount = 0;

// Returns true if the bridge should be animated given the current filter.
static bool bridgePassesFilter(int n1, int n2)
{
    if (s_filterCount == 0) return true;   // no filter — animate all
    for (int i = 0; i < s_filterCount; i++) {
        if ((s_filterPairs[i][0] == n1 && s_filterPairs[i][1] == n2) ||
            (s_filterPairs[i][0] == n2 && s_filterPairs[i][1] == n1))
            return true;
    }
    return false;
}

static constexpr uint32_t TICK_MS    = 30;
static constexpr float    PHASE_STEP = 0.04f;   // ~750 ms full cycle at speed=1

// ── Voltage propagation ────────────────────────────────────────────────────

// Seeds known supply nodes and iterates through all net bridges to spread
// their voltages to connected nodes.  Nodes not reachable from any supply
// remain at -1.0 (unknown).
static void computeNodeVoltages()
{
    for (int i = 0; i < 170; i++) { s_volt[i] = -1.0f; s_from[i] = -1; }

    // Known supply levels (node numbers from pin_map.h)
    s_volt[100] = 0.0f;   // GND
    s_volt[103] = 3.3f;   // +3.3 V
    s_volt[105] = 5.0f;   // +5 V
    // s_from stays -1 for supply seeds — they have no upstream source.

    // Propagate: each pass assigns voltage to any unknown node adjacent to a
    // known one, and records WHICH known node did the assignment (s_from[]).
    // A node is only assigned once, so s_from[] is stable after propagation.
    for (int pass = 0; pass < 16; pass++) {
        bool changed = false;
        for (int n = 0; n < MAX_NETS; n++) {
            for (int b = 0; b < MAX_NODES; b++) {
                int n1 = (int)net[n].bridges[b][0];
                int n2 = (int)net[n].bridges[b][1];
                if (n1 == 0 && n2 == 0) break;
                if (n1 <= 0 || n1 >= 170) continue;
                if (n2 <= 0 || n2 >= 170) continue;

                bool k1 = (s_volt[n1] >= 0.0f);
                bool k2 = (s_volt[n2] >= 0.0f);

                if (k1 && !k2) {
                    s_volt[n2] = s_volt[n1];
                    s_from[n2] = n1;   // n1 passed its voltage to n2
                    changed = true;
                } else if (!k1 && k2) {
                    s_volt[n1] = s_volt[n2];
                    s_from[n1] = n2;   // n2 passed its voltage to n1
                    changed = true;
                }
            }
        }
        if (!changed) break;
    }
}

// ── LED helpers ────────────────────────────────────────────────────────────

static inline uint8_t dimCh(uint8_t v, uint8_t f)
{
    return (uint8_t)(((uint16_t)v * f) >> 8);
}

// Voltage propagation equalises both endpoints of a bridge, so direct voltage
// comparison can't determine direction. Use s_from[] to find the upstream
// node, then orient toward GND on the low-side and away from supply on the
// high-side. Fallback to a raw voltage difference if neither node was a
// propagation source.
static bool bridgeDirection(int n1, int n2, int &n_from, int &n_to)
{
    auto inRange = [](int n) { return n > 0 && n < 170; };

    int upstream = -1, other = -1;
    if (inRange(n2) && s_from[n2] == n1)      { upstream = n1; other = n2; }
    else if (inRange(n1) && s_from[n1] == n2) { upstream = n2; other = n1; }

    if (upstream >= 0) {
        if (!inRange(upstream)) return false;
        float vUp = s_volt[upstream];
        if (vUp < 0.0f) return false;
        if (vUp > 0.05f) { n_from = upstream; n_to = other; }
        else             { n_from = other;    n_to = upstream; }
        return true;
    }

    float v1 = inRange(n1) ? s_volt[n1] : -1.0f;
    float v2 = inRange(n2) ? s_volt[n2] : -1.0f;
    if (v1 < 0.0f || v2 < 0.0f || fabsf(v1 - v2) <= 0.05f) return false;
    if (v1 > v2) { n_from = n1; n_to = n2; }
    else         { n_from = n2; n_to = n1; }
    return true;
}

// ── Drawing helpers ────────────────────────────────────────────────────────

// Additive-white blend: adds a white brightness pulse on top of the existing
// pixel.  factor=255 → full white flash (head), 100 → dim (mid), 35 → faint (tail).
// This makes the comet visible against any wire color, including same-colored
// wires — the head brightens to white, the tail fades back to the wire's hue.
static inline void blendPixel(int idx, const LedMatrix::RGB & /*col*/, uint8_t factor)
{
    if (idx < 0 || idx >= (int)LedMatrix::NUM_LEDS) return;
    uint8_t add = dimCh(255, factor);
    uint32_t existing = LedMatrix::strip().getPixelColor((uint16_t)idx);
    uint8_t er = (existing >> 16) & 0xFF;
    uint8_t eg = (existing >>  8) & 0xFF;
    uint8_t eb = (existing      ) & 0xFF;
    uint16_t nr = (uint16_t)er + add; if (nr > 255) nr = 255;
    uint16_t ng = (uint16_t)eg + add; if (ng > 255) ng = 255;
    uint16_t nb = (uint16_t)eb + add; if (nb > 255) nb = 255;
    LedMatrix::setPixelRGB(idx, (uint8_t)nr, (uint8_t)ng, (uint8_t)nb);
}

// Build path for a same-section bridge (M1↔M1 or M2↔M2).
//
// Finds the wire-body row by counting lit pixels at each row across the full
// column span.  The wire body row has every column lit; endpoint-only rows
// have just the two endpoint columns lit.  Picking the row with the highest
// count gives the correct wire row regardless of which row paintBridgeLeds()
// used — without hardcoding anything.
//
// Falls back to row 0 when the framebuffer is empty (just rebooted).
// Returns path length (buf must hold >= 64 entries).
static int buildSameSectionPath(int n_from, int n_to, int *buf)
{
    bool fromTop = (n_from >= TOP_1 && n_from <= TOP_30);
    int cA   = fromTop ? (n_from - TOP_1) : (n_from - BOTTOM_1);
    int cB   = fromTop ? (n_to   - TOP_1) : (n_to   - BOTTOM_1);
    int step = (cB >= cA) ? 1 : -1;
    int lo   = (cA < cB) ? cA : cB;
    int hi   = (cA > cB) ? cA : cB;

    // Count lit pixels per row across the full column span.
    int wireRow = 0, bestCount = 0;
    for (int r = 0; r < 5; r++) {
        int count = 0;
        for (int c = lo; c <= hi; c++) {
            int idx = fromTop ? (int)LedMatrix::mid1Index((uint8_t)r, (uint8_t)c)
                              : (int)LedMatrix::mid2Index((uint8_t)r, (uint8_t)c);
            if (LedMatrix::frameIsLit(idx)) count++;
        }
        if (count > bestCount) { bestCount = count; wireRow = r; }
    }

    // Build horizontal path at the discovered wire row from cA to cB.
    int len = 0;
    for (int c = cA; c != cB + step; c += step) {
        int idx = fromTop ? (int)LedMatrix::mid1Index((uint8_t)wireRow, (uint8_t)c)
                          : (int)LedMatrix::mid2Index((uint8_t)wireRow, (uint8_t)c);
        if (len < 64) buf[len++] = idx;
    }
    return len;
}

// Draw a comet through an explicit ordered array of LED strip indices.
// The comet head moves through leds[0]→leds[count-1] as t goes 0→1.
static void drawCometPath(const int *leds, int count, float t,
                          const LedMatrix::RGB &col)
{
    if (count <= 0) return;
    int head = (int)(count * t);
    if (head >= count) head = count - 1;

    blendPixel(leds[head],                         col, 255);
    if (head > 0) blendPixel(leds[head - 1],       col, 100);
    if (head > 1) blendPixel(leds[head - 2],       col,  35);
}

// Build the LED path for a cross-section bridge by walking every candidate
// LED in the expected paint order and keeping only those the framebuffer
// confirms are actually lit.  This guarantees the comet follows exactly the
// pixels paintBridgeLeds painted, regardless of any path-calculation
// differences.
//
// Candidate order (TOP → BOTTOM):
//   M1 rows 0–4 at cTop   (M1 column — endpoints at row 0, wire at rows 1-4)
//   M2 rows 0–4 at cTop   (M2 entry column)
//   M2 row  1 cTop..cBot  (horizontal routing, may overlap above)
//   M2 rows 0–4 at cBot   (M2 destination column)
//
// BOTTOM → TOP uses the reverse order.
// Returns path length (buf must hold ≥ 64 entries).
static int buildCrossPath(int n_from, int n_to, int *buf)
{
    // Collect all candidates, then filter through the framebuffer.
    static int cand[64];
    int clen = 0;

    bool fromIsTop = (n_from >= TOP_1 && n_from <= TOP_30);
    int cTop = fromIsTop ? (n_from - TOP_1) : (n_to   - TOP_1);
    int cBot = fromIsTop ? (n_to - BOTTOM_1) : (n_from - BOTTOM_1);
    int step = (cBot >= cTop) ? 1 : -1;

    auto addCand = [&](int idx) {
        if (clen < 64) cand[clen++] = idx;
    };

    if (fromIsTop) {
        // TOP → BOTTOM
        for (int r = 0; r < 5; r++) addCand((int)LedMatrix::mid1Index((uint8_t)r, (uint8_t)cTop));
        for (int r = 0; r < 5; r++) addCand((int)LedMatrix::mid2Index((uint8_t)r, (uint8_t)cTop));
        for (int c = cTop + step; c != cBot + step; c += step)
            addCand((int)LedMatrix::mid2Index(1, (uint8_t)c));
        for (int r = 0; r < 5; r++) addCand((int)LedMatrix::mid2Index((uint8_t)r, (uint8_t)cBot));
    } else {
        // BOTTOM → TOP (reverse)
        for (int r = 4; r >= 0; r--) addCand((int)LedMatrix::mid2Index((uint8_t)r, (uint8_t)cBot));
        for (int c = cBot - step; c != cTop - step; c -= step)
            addCand((int)LedMatrix::mid2Index(1, (uint8_t)c));
        for (int r = 4; r >= 0; r--) addCand((int)LedMatrix::mid2Index((uint8_t)r, (uint8_t)cTop));
        for (int r = 4; r >= 0; r--) addCand((int)LedMatrix::mid1Index((uint8_t)r, (uint8_t)cTop));
    }

    // Keep only lit candidates, de-duplicating by index.
    int len = 0;
    for (int i = 0; i < clen; i++) {
        int idx = cand[i];
        if (!LedMatrix::frameIsLit(idx)) continue;
        bool dup = false;
        for (int j = 0; j < len; j++) { if (buf[j] == idx) { dup = true; break; } }
        if (!dup && len < 64) buf[len++] = idx;
    }
    return len;
}

// ── Public API ─────────────────────────────────────────────────────────────

void enable(bool on, float speed)
{
    s_enabled = on;
    s_speed   = (speed < 0.1f) ? 0.1f : speed;
    if (!on)
        LedMatrix::frameApplyFull();
}

bool isEnabled() { return s_enabled; }

void setFilter(const int *pairs, int count)
{
    s_filterCount = 0;
    if (!pairs || count <= 0) return;
    int n = (count < MAX_FILTER_PAIRS) ? count : MAX_FILTER_PAIRS;
    for (int i = 0; i < n; i++) {
        s_filterPairs[i][0] = (int16_t)pairs[i * 2];
        s_filterPairs[i][1] = (int16_t)pairs[i * 2 + 1];
    }
    s_filterCount = n;
}

void clearFilter()
{
    s_filterCount = 0;
}

void tick()
{
    if (!s_enabled) return;

    uint32_t now = millis();
    if (now - s_lastTick < TICK_MS) return;
    s_lastTick = now;

    // Recompute which node is at which potential (cheap — exits early when stable).
    computeNodeVoltages();

    // Load static framebuffer into NeoPixel buffer without pushing to hardware yet.
    LedMatrix::frameApplyToBuffer();

    for (int n = 8; n < MAX_NETS; n++)
    {
        if (net[n].nodes[0] == 0) continue;

        s_phase[n] += PHASE_STEP * s_speed;
        if (s_phase[n] >= 1.0f) s_phase[n] -= 1.0f;

        const LedMatrix::RGB &col = net[n].color;

        for (int b = 0; b < MAX_NODES; b++)
        {
            int n1 = (int)net[n].bridges[b][0];
            int n2 = (int)net[n].bridges[b][1];
            if (n1 == 0 && n2 == 0) break;

            if (!bridgePassesFilter(n1, n2)) continue;

            // Determine current direction.  Skip bridges where direction is
            // unknown (not reachable from any supply, or ambiguous).
            int n_from, n_to;
            if (!bridgeDirection(n1, n2, n_from, n_to)) continue;

            bool fromTop = (n_from >= TOP_1    && n_from <= TOP_30);
            bool fromBot = (n_from >= BOTTOM_1 && n_from <= BOTTOM_30);
            bool toTop   = (n_to   >= TOP_1    && n_to   <= TOP_30);
            bool toBot   = (n_to   >= BOTTOM_1 && n_to   <= BOTTOM_30);

            if ((fromTop && toTop) || (fromBot && toBot)) {
                // Same-section: scan the framebuffer to find the actual painted
                // pixels — no hardcoded row.  Works for both M1↔M1 and M2↔M2.
                int pathBuf[64];
                int pathLen = buildSameSectionPath(n_from, n_to, pathBuf);
                drawCometPath(pathBuf, pathLen, s_phase[n], col);

            } else if ((fromTop && toBot) || (fromBot && toTop)) {
                // Cross-section: follow the L-shaped painted path
                int pathBuf[64];
                int pathLen = buildCrossPath(n_from, n_to, pathBuf);
                drawCometPath(pathBuf, pathLen, s_phase[n], col);
            }
            // Bridges involving non-breadboard nodes (GND, 5V, NANO, EXT…)
            // have no LED position — silently skipped.
        }
    }

    LedMatrix::show();
}

}  // namespace CurrentViz
