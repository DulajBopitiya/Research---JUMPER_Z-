#include "current_viz.h"
#include "path_mapping_algo.h"   // net[], MAX_NETS, MAX_NODES
#include "Led_Matrix.h"
#include "pin_map.h"

// Current direction is determined automatically by propagating known supply
// voltages through the connected nets:
//
//   GND  (node 100) = 0.0 V
//   3.3V (node 103) = 3.3 V
//   5V   (node 105) = 5.0 V
//
// For each bridge, if one node has higher potential than the other the comet
// travels high→low (conventional current direction).  If both potentials are
// equal or unknown (e.g. no power node in the net), the bridge falls back to
// bidirectional (two comets half-phase apart) so something is always visible.

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

static constexpr uint32_t TICK_MS    = 30;
static constexpr float    PHASE_STEP = 0.04f;   // ~750 ms full cycle at speed=1

// ── Voltage propagation ────────────────────────────────────────────────────

// Seeds known supply nodes and iterates through all net bridges to spread
// their voltages to connected nodes.  Nodes not reachable from any supply
// remain at -1.0 (unknown).
static void computeNodeVoltages()
{
    for (int i = 0; i < 170; i++) s_volt[i] = -1.0f;

    // Known supply levels (node numbers from pin_map.h)
    s_volt[100] = 0.0f;   // GND
    s_volt[103] = 3.3f;   // +3.3 V
    s_volt[105] = 5.0f;   // +5 V

    // Propagate through every bridge until no more assignments (≤16 passes).
    for (int pass = 0; pass < 16; pass++) {
        bool changed = false;
        for (int n = 0; n < MAX_NETS; n++) {
            for (int b = 0; b < MAX_NODES; b++) {
                int n1 = (int)net[n].bridges[b][0];
                int n2 = (int)net[n].bridges[b][1];
                if (n1 == 0 && n2 == 0) break;          // end of bridge chain
                if (n1 <= 0 || n1 >= 170) continue;
                if (n2 <= 0 || n2 >= 170) continue;

                bool k1 = (s_volt[n1] >= 0.0f);
                bool k2 = (s_volt[n2] >= 0.0f);

                if  (k1 && !k2) { s_volt[n2] = s_volt[n1]; changed = true; }
                else if (!k1 && k2) { s_volt[n1] = s_volt[n2]; changed = true; }
                // Both known or both unknown: leave as-is.
            }
        }
        if (!changed) break;  // stable — done early
    }
}

// ── LED helpers ────────────────────────────────────────────────────────────

static int nodeToLed(int node)
{
    if (node >= TOP_1 && node <= TOP_30)
        return (int)LedMatrix::mid1Index(0, (uint8_t)(node - TOP_1));
    if (node >= BOTTOM_1 && node <= BOTTOM_30)
        return (int)LedMatrix::mid2Index(0, (uint8_t)(node - BOTTOM_1));
    return -1;
}

static inline uint8_t dimCh(uint8_t v, uint8_t f)
{
    return (uint8_t)(((uint16_t)v * f) >> 8);
}

// Column step: 5 for within M1 or M2 (column-major, 5 rows), else 1.
static int colStepFor(int ledA, int ledB)
{
    bool bothM1 = (ledA >= 50 && ledA < 200) && (ledB >= 50 && ledB < 200);
    bool bothM2 = (ledA >= 200 && ledA < 350) && (ledB >= 200 && ledB < 350);
    return (bothM1 || bothM2) ? 5 : 1;
}

// Draw one comet travelling from ledA → ledB at phase t ∈ [0, 1).
// Uses max-blend so two overlapping comets add brightness rather than
// one silently overwriting the other.
static void drawComet(int ledA, int ledB, float t,
                      const LedMatrix::RGB &col, int colStep)
{
    if (ledA == ledB || colStep <= 0) return;

    int range  = ledB - ledA;
    int dir    = (range > 0) ? 1 : -1;
    int steps  = abs(range) / colStep;
    if (steps == 0) return;

    int cur = (int)(steps * t);
    if (cur >= steps) cur = steps - 1;

    int head = ledA + dir * cur * colStep;
    int lo   = (ledA < ledB) ? ledA : ledB;
    int hi   = (ledA > ledB) ? ledA : ledB;

    auto blendAt = [&](int idx, uint8_t factor) {
        if (idx < lo || idx > hi) return;
        uint8_t nr = dimCh(col.r, factor);
        uint8_t ng = dimCh(col.g, factor);
        uint8_t nb = dimCh(col.b, factor);
        uint32_t existing = LedMatrix::strip().getPixelColor((uint16_t)idx);
        uint8_t er = (existing >> 16) & 0xFF;
        uint8_t eg = (existing >>  8) & 0xFF;
        uint8_t eb = (existing      ) & 0xFF;
        LedMatrix::setPixelRGB(idx,
            nr > er ? nr : er,
            ng > eg ? ng : eg,
            nb > eb ? nb : eb);
    };

    blendAt(head,                  255);
    blendAt(head - dir * colStep,  100);
    blendAt(head - dir * colStep*2, 35);
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

            int led1 = nodeToLed(n1);
            int led2 = nodeToLed(n2);
            if (led1 < 0 || led2 < 0) continue;

            int cs = colStepFor(led1, led2);

            float v1 = (n1 > 0 && n1 < 170) ? s_volt[n1] : -1.0f;
            float v2 = (n2 > 0 && n2 < 170) ? s_volt[n2] : -1.0f;

            if (v1 >= 0.0f && v2 >= 0.0f && v1 > v2 + 0.05f) {
                // n1 is higher potential — current flows led1 → led2 (conventional)
                drawComet(led1, led2, s_phase[n], col, cs);

            } else if (v1 >= 0.0f && v2 >= 0.0f && v2 > v1 + 0.05f) {
                // n2 is higher potential — current flows led2 → led1
                drawComet(led2, led1, s_phase[n], col, cs);

            } else {
                // Both potentials equal or unknown — bidirectional fallback
                float rev = s_phase[n] + 0.5f;
                if (rev >= 1.0f) rev -= 1.0f;
                drawComet(led1, led2, s_phase[n], col, cs);
                drawComet(led2, led1, rev,        col, cs);
            }
        }
    }

    LedMatrix::show();
}

}  // namespace CurrentViz
