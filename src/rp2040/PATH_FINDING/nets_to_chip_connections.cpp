#include "nets_to_chip_connections.h"

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

// Convert NANO_D0..NANO_A7 node constant → 0-23 index into nano.* arrays.
static int nanoNodeToIndex(int node)
{
    return node - NANO_D0; // NANO_D0 = 70  →  D0=0, A7=23
}

// Search chips I/J/K/L (ch[8..11]) xMap for a SF node.
// Returns chip index (8-11) or -1.
static int findChipForSFNode(int node)
{
    for (int c = 8; c <= 11; c++) {
        for (int x = 0; x < 16; x++) {
            if (ch[c].xMap[x] == node) return c;
        }
    }
    return -1;
}

// Populate up to 3 candidate chip slots with every chip that has 'node'
// in its xMap.  Some SF nodes (e.g. SUPPLY_5V) appear on multiple chips
// (CHIP_J and CHIP_L).  Returning all of them lets resolveChipCandidates
// find a shared chip with the other node and avoid unnecessary alt-paths.
static void findAllChipsForSFNode(int node, int candidates[3])
{
    int found = 0;
    for (int c = 8; c <= 11 && found < 3; c++) {
        for (int x = 0; x < 16; x++) {
            if (ch[c].xMap[x] == node) { candidates[found++] = c; break; }
        }
    }
}

// Search chExt[0..1] xMap for an EXT pin node.
// Returns chip number (CHIP_I=8 or CHIP_J=9) or -1.
static int findChipForEXTNode(int node)
{
    for (int e = 0; e < 2; e++) {
        for (int x = 0; x < 16; x++) {
            if (chExt[e].xMap[x] == node) return chExt[e].chipNumber;
        }
    }
    return -1;
}

// Count how many X lines on a chip are currently active (xStatus >= 0).
static int countChipConnections(int chipNum)
{
    int count = 0;
    for (int x = 0; x < 16; x++) {
        if (ch[chipNum].xStatus[x] >= 0) count++;
    }
    return count;
}

// From a candidates[3] array, return the chip with the fewest active X lines.
// Ignores -1 (unused) slots.
static int leastCrowdedChip(int candidates[3])
{
    int best = -1, bestCount = 9999;
    for (int i = 0; i < 3; i++) {
        if (candidates[i] == -1) continue;
        int c = countChipConnections(candidates[i]);
        if (c < bestCount) {
            bestCount = c;
            best      = candidates[i];
        }
    }
    return best;
}

// Ordering used to normalise node1/node2: lower value → node1.
// BB(0) < NANO(1) < EXT(2) < SF(3) < BBL(4)
static int nodeTypePrecedence(nodeType t)
{
    switch (t) {
        case BB:   return 0;
        case NANO: return 1;
        case EXT:  return 2;
        case SF:   return 3;
        case BBL:  return 4;
    }
    return 0;
}

// ---------------------------------------------------------------------------
// Public: getNodeType
// ---------------------------------------------------------------------------
nodeType getNodeType(int node)
{
    // Breadboard nodes TOP_1(1) – BOTTOM_30(60)
    // Nodes that map to CHIP_L are rail endpoints → BBL
    if (node >= TOP_1 && node <= BOTTOM_30) {
        if (bbNodesToChip[node] == CHIP_L) return BBL;
        return BB;
    }
    // Arduino Nano header pins
    if (node >= NANO_D0 && node <= NANO_A7) return NANO;
    // Special-function nodes (GND, rails, DACs, ADCs, GPIOs …)
    if (node >= GND && node <= EMPTY_NET) return SF;
    // External 40-pin header pins
    if (node >= EXT_RESET) return EXT;

    return SF; // fallback
}

// ---------------------------------------------------------------------------
// Stage 1: bridgesToPaths
// Flatten every net's bridges[][2] into the global path[] array.
// ---------------------------------------------------------------------------
int numberOfPaths = 0;

int bridgesToPaths()
{
    numberOfPaths = 0;

    for (int n = 0; n < MAX_NETS; n++) {
        for (int b = 0; b < MAX_NODES; b++) {
            int n1 = net[n].bridges[b][0];
            int n2 = net[n].bridges[b][1];

            if (n1 == 0 && n2 == 0) break;          // end of this net's bridges
            if (numberOfPaths >= MAX_BRIDGES) return numberOfPaths;

            pathStruct &p = path[numberOfPaths];

            p.node1 = n1;
            p.node2 = n2;
            p.net   = net[n].number;

            for (int i = 0; i < 6; i++) p.chip[i] = -1;
            for (int i = 0; i < 6; i++) { p.x[i] = -1; p.y[i] = -1; }
            for (int i = 0; i < 3; i++)
                for (int j = 0; j < 3; j++)
                    p.candidates[i][j] = -1;

            p.altPathNeeded = 0;
            p.sameChip      = false;
            p.Lchip         = false;
            p.skip          = false;
            p.duplicate     = 0;

            numberOfPaths++;
        }
    }
    return numberOfPaths;
}

// ---------------------------------------------------------------------------
// Stage 2: findStartAndEndChips
// For each path, populate candidates[nd][0..2] with possible chips for each
// node. Multiple candidates occur for Nano pins that connect to both I and K,
// for example. SF/EXT nodes have exactly one chip.
// ---------------------------------------------------------------------------
void findStartAndEndChips()
{
    for (int i = 0; i < numberOfPaths; i++) {
        if (path[i].skip) continue;

        for (int nd = 0; nd < 2; nd++) {
            int      node = (nd == 0) ? path[i].node1 : path[i].node2;
            nodeType nt   = getNodeType(node);

            // Clear candidates for this node slot
            for (int j = 0; j < 3; j++) path[i].candidates[nd][j] = -1;

            if (nt == BB || nt == BBL) {
                // Direct single-chip lookup via bbNodesToChip[]
                path[i].candidates[nd][0] = bbNodesToChip[node];

            } else if (nt == NANO) {
                int idx = nanoNodeToIndex(node);
                // Primary candidate: the I or J chip this pin connects to
                path[i].candidates[nd][0] = nano.mapIJ[idx];
                // Secondary candidate: K or L if this pin also reaches one
                if (nano.mapKL[idx] != -1)
                    path[i].candidates[nd][1] = nano.mapKL[idx];

            } else if (nt == SF) {
                // Fill all chips that carry this node (some SF nodes like
                // SUPPLY_5V appear on both CHIP_J and CHIP_L — returning all
                // lets resolveChipCandidates find the shared-chip overlap).
                findAllChipsForSFNode(node, path[i].candidates[nd]);

            } else if (nt == EXT) {
                // Search chExt I, J for this external pin
                path[i].candidates[nd][0] = findChipForEXTNode(node);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Stage 3: assignPathType
// Classify the connection and normalise so node1 always has the lower
// precedence type (BB < NANO < EXT < SF < BBL).
// ---------------------------------------------------------------------------
void assignPathType()
{
    for (int i = 0; i < numberOfPaths; i++) {
        if (path[i].skip) continue;

        nodeType t1 = getNodeType(path[i].node1);
        nodeType t2 = getNodeType(path[i].node2);

        // Swap so lower-precedence type is always node1
        if (nodeTypePrecedence(t1) > nodeTypePrecedence(t2)) {
            int tmp       = path[i].node1;
            path[i].node1 = path[i].node2;
            path[i].node2 = tmp;

            for (int j = 0; j < 3; j++) {
                int tc                  = path[i].candidates[0][j];
                path[i].candidates[0][j] = path[i].candidates[1][j];
                path[i].candidates[1][j] = tc;
            }
            nodeType tt = t1; t1 = t2; t2 = tt;
        }

        path[i].nodeType[0] = t1;
        path[i].nodeType[1] = t2;

        // ── Assign path type ──────────────────────────────────────────────
        if      (t1 == BB   && t2 == BB)   path[i].pathType = BBtoBB;
        else if (t1 == BB   && t2 == NANO) path[i].pathType = BBtoNANO;
        else if (t1 == BB   && t2 == EXT)  path[i].pathType = BBtoEXT;
        else if (t1 == BB   && t2 == SF)   path[i].pathType = BBtoSF;
        else if (t1 == BB   && t2 == BBL)  path[i].pathType = BBtoBBL;
        else if (t1 == NANO && t2 == NANO) path[i].pathType = NANOtoNANO;
        else if (t1 == NANO && t2 == EXT)  path[i].pathType = NANOtoEXT;
        else if (t1 == NANO && t2 == SF)   path[i].pathType = NANOtoSF;
        else if (t1 == NANO && t2 == BBL)  path[i].pathType = NANOtoBBL;
        else if (t1 == EXT  && t2 == EXT)  path[i].pathType = EXTtoEXT;
        else if (t1 == EXT  && t2 == SF)   path[i].pathType = EXTtoSF;
        else if (t1 == EXT  && t2 == BBL)  path[i].pathType = EXTtoBBL;
        else if (t1 == SF   && t2 == SF)   path[i].pathType = SFtoSF;
        else if (t1 == SF   && t2 == BBL)  path[i].pathType = SFtoBBL;
        else if (t1 == BBL  && t2 == BBL)  path[i].pathType = BBLtoBBL;
        else                               path[i].pathType = BBtoBB; // fallback

        // Flag if Chip L is a candidate for either node (used in commitPaths)
        if (path[i].candidates[0][0] == CHIP_L ||
            path[i].candidates[1][0] == CHIP_L)
            path[i].Lchip = true;
    }
}

// ---------------------------------------------------------------------------
// Stage 4: resolveChipCandidates
// Collapse each path's candidate lists to a single chip per node.
//
// Strategy:
//   1. If both nodes share a candidate chip → assign both to it (sameChip).
//   2. Otherwise → assign each node its least-crowded candidate chip and
//      flag altPathNeeded for non-BBtoBB paths (they need multi-hop routing).
//
// BBtoBB is the special case: chips A-H are fully interconnected via the
// X-line mesh, so two different chips can still be connected in one step.
// ---------------------------------------------------------------------------
void resolveChipCandidates()
{
    for (int i = 0; i < numberOfPaths; i++) {
        if (path[i].skip) continue;

        // ── 1. Look for an overlapping candidate chip ─────────────────────
        int overlap = -1;
        for (int a = 0; a < 3 && overlap == -1; a++) {
            if (path[i].candidates[0][a] == -1) continue;
            for (int b = 0; b < 3; b++) {
                if (path[i].candidates[1][b] == -1) continue;
                if (path[i].candidates[0][a] == path[i].candidates[1][b]) {
                    overlap = path[i].candidates[0][a];
                    break;
                }
            }
        }

        if (overlap != -1) {
            // Direct single-chip connection
            path[i].chip[0]  = overlap;
            path[i].chip[1]  = overlap;
            path[i].sameChip = true;
        } else {
            // Assign each node to its own least-crowded chip
            path[i].chip[0] = leastCrowdedChip(path[i].candidates[0]);
            path[i].chip[1] = leastCrowdedChip(path[i].candidates[1]);

            // BBtoBB: chips A-H interconnect via the X-bus, so cross-chip
            // routes are handled natively — no alt path needed.
            // All other types need a multi-hop route through Chip L.
            if (path[i].pathType != BBtoBB) {
                path[i].altPathNeeded = 1;
            }
        }

        // ── 2. Update Lchip flag from resolved chips ──────────────────────
        if (path[i].chip[0] == CHIP_L || path[i].chip[1] == CHIP_L)
            path[i].Lchip = true;
    }
}

// ---------------------------------------------------------------------------
// Top-level: run all 4 stages in sequence
// ---------------------------------------------------------------------------
void netsToChipConnections()
{
    bridgesToPaths();
    findStartAndEndChips();
    assignPathType();
    resolveChipCandidates();
}

// ===========================================================================
// Stage 5: commitPaths
//
// Fills path[i].x[] / path[i].y[] — the actual CH446Q switch coordinates.
//
// How the physical topology maps to commands (see chip xMap/yMap in
// path_mapping_algo.cpp for the full wiring):
//
//   BB chips (A-H):
//     Y lines  → breadboard rows (TOP_2..TOP_8, BOTTOM_2..BOTTOM_8) + CHIP_L bus
//     X lines  → buses to other chips (CHIP_I, CHIP_J, CHIP_K, CHIP_L, and
//                the two lanes to every other BB chip)
//
//   SF chips (I-L):
//     X lines  → Nano pins / EXT pins / SF nodes (GND, DAC, ADC …)
//     Y lines  → buses back to each BB chip (Y0=CHIP_A, Y1=CHIP_B … Y7=CHIP_H)
//
// Two-hop example — TOP_5 ↔ NANO_D3:
//   CHIP_A: close X0(CHIP_I bus) ↔ Y4(TOP_5)
//   CHIP_I: close X3(NANO_D3)   ↔ Y0(CHIP_A bus)
//
// Three-hop example — TOP_5 ↔ TOP_1 (BBtoBBL, TOP_1 is on CHIP_L):
//   CHIP_A: close Xfree ↔ Y4(TOP_5)
//   CHIP_A: close Xfree ↔ Y0(CHIP_L bus)   ← same X, bridges node1 to L-bus
//   CHIP_L: close X8(TOP_1) ↔ Y0(CHIP_A bus)
// ===========================================================================

// ── Stage-5 helpers ──────────────────────────────────────────────────────────

// Search ch[chip].xMap[] for 'node'. Returns the x index, or -1.
// lane selects which occurrence to return (0 = first, 1 = second …).
// Used for the "bus" connections: X lines on BB chips point to SF/BB chips,
// and X lines on SF chips point to Nano/SF/EXT nodes.
static int xIndexForNodeOnChip(int node, int chip, int lane = 0)
{
    int found = 0;
    for (int x = 0; x < 16; x++) {
        if (ch[chip].xMap[x] == node) {
            if (found == lane) return x;
            found++;
        }
    }
    return -1;
}

// Search ch[chip].yMap[] for 'node'. Returns the y index, or -1.
// Y lines on BB chips = breadboard rows + CHIP_L bus.
// Y lines on SF chips = BB-chip buses (Y0=CHIP_A, Y1=CHIP_B …).
//
// startY: pass 1 when searching for a real BB row node on a BB chip to skip
// Y0, which is always the CHIP_L inter-chip bus sentinel (value 11 = CHIP_L).
// Without this, TOP_11 (also value 11) collides with CHIP_L at Y0 and the
// search returns the wrong index.
static int yIndexForNodeOnChip(int node, int chip, int startY = 0)
{
    for (int y = startY; y < 8; y++) {
        if (ch[chip].yMap[y] == node) return y;
    }
    return -1;
}

// Search chExt[0..1].xMap[] for an EXT node on a given chip number.
// Returns the x index, or -1.
static int xIndexForExtNodeOnChip(int node, int chipNumber)
{
    for (int e = 0; e < 2; e++) {
        if (chExt[e].chipNumber != chipNumber) continue;
        for (int x = 0; x < 16; x++) {
            if (chExt[e].xMap[x] == node) return x;
        }
    }
    return -1;
}

// Return the first X index on chip whose xStatus is -1 (unused).
static int findFreeXOnChip(int chip)
{
    for (int x = 0; x < 16; x++) {
        if (ch[chip].xStatus[x] == -1) return x;
    }
    return -1;
}

// Return the first Y index on chip whose yStatus is -1 (unused).
static int findFreeYOnChip(int chip)
{
    for (int y = 0; y < 8; y++) {
        if (ch[chip].yStatus[y] == -1) return y;
    }
    return -1;
}

// Resolve the X index for any node type on its assigned chip.
// Handles BB (Y lookup), NANO/SF (X lookup in ch[]), EXT (X lookup in chExt[]).
static int resolveXForNode(int node, int chip, nodeType nt)
{
    if (nt == EXT) return xIndexForExtNodeOnChip(node, chip);
    return xIndexForNodeOnChip(node, chip);
}

// ---------------------------------------------------------------------------
// Stage 5: commitPaths
// ---------------------------------------------------------------------------
void commitPaths()
{
    for (int i = 0; i < numberOfPaths; i++) {
        if (path[i].skip) continue;

        const int c0  = path[i].chip[0];
        const int c1  = path[i].chip[1];
        const int n1  = path[i].node1;
        const int n2  = path[i].node2;
        const int net = path[i].net;

        switch (path[i].pathType) {

        // ── BBtoBB ───────────────────────────────────────────────────────────
        // BB nodes live on the Y lines of their chip.
        case BBtoBB:
            if (path[i].sameChip) {
                // Both Y lines on one chip → bridge via any free X on that chip.
                int y0 = yIndexForNodeOnChip(n1, c0, 1); // skip Y0 (CHIP_L bus)
                int y1 = yIndexForNodeOnChip(n2, c0, 1);
                int x  = findFreeXOnChip(c0);
                if (x == -1 || y0 == -1 || y1 == -1) { path[i].skip = true; break; }
                path[i].chip[0] = c0; path[i].x[0] = x; path[i].y[0] = y0;
                path[i].chip[1] = c0; path[i].x[1] = x; path[i].y[1] = y1;
                ch[c0].xStatus[x] = (int16_t)net;
            } else {
                // Cross-chip: each chip has an X line that is a shared bus trace
                // to the other chip (two lanes in xMap — pick lane 0 here).
                int y0 = yIndexForNodeOnChip(n1, c0, 1); // skip Y0 (CHIP_L bus)
                int x0 = xIndexForNodeOnChip(c1, c0, 0); // c0-side bus to c1
                int x1 = xIndexForNodeOnChip(c0, c1, 0); // c1-side bus back to c0
                int y1 = yIndexForNodeOnChip(n2, c1, 1);
                if (x0 == -1 || y0 == -1 || x1 == -1 || y1 == -1) { path[i].skip = true; break; }
                path[i].chip[0] = c0; path[i].x[0] = x0; path[i].y[0] = y0;
                path[i].chip[1] = c1; path[i].x[1] = x1; path[i].y[1] = y1;
                ch[c0].xStatus[x0] = (int16_t)net;
                ch[c1].xStatus[x1] = (int16_t)net;
            }
            break;

        // ── BBtoNANO / BBtoSF / BBtoEXT ──────────────────────────────────────
        // node1 = BB row (Y on BB chip c0)
        // node2 = Nano/SF/EXT node (X on SF chip c1)
        //   Hop 0 (BB chip c0): X = bus line going to c1, Y = BB row
        //   Hop 1 (SF chip c1): X = node2's line,         Y = bus back to c0
        //
        // Special sub-case BBtoSF where c1 == CHIP_L:
        //   BB chips' xMap never contains CHIP_L, so x0 = -1 and the path
        //   would be skipped. Use the same 3-hop routing as BBtoBBL instead:
        //   BB chip c0: Xfree ↔ Y(n1)       — n1 row on c0
        //   BB chip c0: Xfree ↔ Y0(CHIP_L)  — same Xfree, bridges to ChipL bus
        //   CHIP_L:     X(n2) ↔ Y(c0)       — connects SF node to c0 bus
        case BBtoNANO:
        case BBtoSF:
        case BBtoEXT:
        {
            if (path[i].pathType == BBtoSF && c1 == CHIP_L) {
                int y_n1 = yIndexForNodeOnChip(n1, c0, 1); // skip Y0 (CHIP_L bus)
                int y_L  = yIndexForNodeOnChip(CHIP_L, c0); // CHIP_L bus sentinel at Y0
                int x_bb = findFreeXOnChip(c0);
                int x_n2 = xIndexForNodeOnChip(n2, CHIP_L);
                int y_c0 = yIndexForNodeOnChip(c0, CHIP_L);
                if (y_n1==-1 || y_L==-1 || x_bb==-1 || x_n2==-1 || y_c0==-1) { path[i].skip=true; break; }
                path[i].chip[0] = c0;     path[i].x[0] = x_bb; path[i].y[0] = y_n1;
                path[i].chip[1] = c0;     path[i].x[1] = x_bb; path[i].y[1] = y_L;
                path[i].chip[2] = CHIP_L; path[i].x[2] = x_n2; path[i].y[2] = y_c0;
                ch[c0].xStatus[x_bb]     = (int16_t)net;
                ch[CHIP_L].xStatus[x_n2] = (int16_t)net;
                break;
            }
            int y0 = yIndexForNodeOnChip(n1, c0, 1); // skip Y0 (CHIP_L bus)
            int x0 = xIndexForNodeOnChip(c1, c0, 0);
            int x1 = resolveXForNode(n2, c1, path[i].nodeType[1]);
            int y1 = yIndexForNodeOnChip(c0, c1);
            if (x0 == -1 || y0 == -1 || x1 == -1 || y1 == -1) { path[i].skip = true; break; }
            path[i].chip[0] = c0; path[i].x[0] = x0; path[i].y[0] = y0;
            path[i].chip[1] = c1; path[i].x[1] = x1; path[i].y[1] = y1;
            ch[c0].xStatus[x0] = (int16_t)net;
            ch[c1].xStatus[x1] = (int16_t)net;
        }
        break;

        // ── NANOtoSF / EXTtoSF / NANOtoEXT / EXTtoEXT ───────────────────────
        // Both nodes are X lines on SF chips.
        // Same chip: bridge both X lines to the same free Y (a BB-chip bus).
        // Different chips: flag for resolveAltPaths (needs 3-hop routing).
        case NANOtoSF:
        case EXTtoSF:
        case NANOtoEXT:
        case EXTtoEXT:
            if (path[i].sameChip) {
                int x0 = resolveXForNode(n1, c0, path[i].nodeType[0]);
                int x1 = resolveXForNode(n2, c0, path[i].nodeType[1]);
                int y  = findFreeYOnChip(c0);
                if (x0 == -1 || x1 == -1 || y == -1) { path[i].skip = true; break; }
                path[i].chip[0] = c0; path[i].x[0] = x0; path[i].y[0] = y;
                path[i].chip[1] = c0; path[i].x[1] = x1; path[i].y[1] = y;
                ch[c0].xStatus[x0] = (int16_t)net;
                ch[c0].xStatus[x1] = (int16_t)net;
                ch[c0].yStatus[y]  = (int16_t)net;
            } else {
                path[i].altPathNeeded = 1;
            }
            break;

        // ── BBtoBBL ───────────────────────────────────────────────────────────
        // node1 = regular BB row (Y on BB chip c0)
        // node2 = rail endpoint (X on CHIP_L; CHIP_L's Y connects back to c0)
        // Requires 3 switch commands:
        //   cmd 0: BB chip c0 → Xfree ↔ Y(node1)
        //   cmd 1: BB chip c0 → Xfree ↔ Y0(CHIP_L bus)   ← same Xfree as cmd 0
        //   cmd 2: CHIP_L     → X(node2) ↔ Y(c0 bus)
        case BBtoBBL:
        {
            int y_n1 = yIndexForNodeOnChip(n1, c0);
            int y_L  = yIndexForNodeOnChip(CHIP_L, c0); // CHIP_L bus is Y0 on all BB chips
            int x_bb = findFreeXOnChip(c0);
            int x_n2 = xIndexForNodeOnChip(n2, CHIP_L);
            int y_c0 = yIndexForNodeOnChip(c0, CHIP_L);
            if (y_n1==-1 || y_L==-1 || x_bb==-1 || x_n2==-1 || y_c0==-1) { path[i].skip=true; break; }
            path[i].chip[0] = c0;     path[i].x[0] = x_bb; path[i].y[0] = y_n1;
            path[i].chip[1] = c0;     path[i].x[1] = x_bb; path[i].y[1] = y_L;
            path[i].chip[2] = CHIP_L; path[i].x[2] = x_n2; path[i].y[2] = y_c0;
            ch[c0].xStatus[x_bb]    = (int16_t)net;
            ch[CHIP_L].xStatus[x_n2] = (int16_t)net;
        }
        break;

        // ── NANOtoNANO (same chip) ────────────────────────────────────────────
        // Both Nano pins are X lines on the same SF chip → same pattern as NANOtoSF.
        case NANOtoNANO:
            if (path[i].sameChip) {
                int x0 = xIndexForNodeOnChip(n1, c0);
                int x1 = xIndexForNodeOnChip(n2, c0);
                int y  = findFreeYOnChip(c0);
                if (x0==-1 || x1==-1 || y==-1) { path[i].skip=true; break; }
                path[i].chip[0] = c0; path[i].x[0] = x0; path[i].y[0] = y;
                path[i].chip[1] = c0; path[i].x[1] = x1; path[i].y[1] = y;
                ch[c0].xStatus[x0] = (int16_t)net;
                ch[c0].xStatus[x1] = (int16_t)net;
                ch[c0].yStatus[y]  = (int16_t)net;
            } else {
                // Different SF chips → needs 3-hop via a BB chip bus
                path[i].altPathNeeded = 1;
            }
            break;

        // ── SFtoSF ────────────────────────────────────────────────────────────
        // Both SF nodes are X lines. If they share a chip (e.g. SUPPLY_5V and
        // ISENSE_PLUS are both X lines on CHIP_L), connect them directly via a
        // free Y line on that chip — same pattern as NANOtoNANO same-chip.
        // Different chips fall through to resolveAltPaths.
        case SFtoSF:
            if (path[i].sameChip) {
                int x0 = xIndexForNodeOnChip(n1, c0);
                int x1 = xIndexForNodeOnChip(n2, c0);
                int y  = findFreeYOnChip(c0);
                if (x0==-1 || x1==-1 || y==-1) { path[i].skip=true; break; }
                path[i].chip[0] = c0; path[i].x[0] = x0; path[i].y[0] = y;
                path[i].chip[1] = c0; path[i].x[1] = x1; path[i].y[1] = y;
                ch[c0].xStatus[x0] = (int16_t)net;
                ch[c0].xStatus[x1] = (int16_t)net;
                ch[c0].yStatus[y]  = (int16_t)net;
            } else {
                path[i].altPathNeeded = 1;
            }
            break;

        // ── Remaining types: handled in resolveAltPaths ──────────────────────
        case NANOtoBBL:
        case SFtoBBL:
        case EXTtoBBL:
        case BBLtoBBL:
            path[i].altPathNeeded = 1;
            break;

        default:
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Stage 6: resolveAltPaths
//
// Handles the altPathNeeded cases that commitPaths() deferred.
// Currently resolves NANOtoNANO and EXTtoEXT across two different SF chips
// by routing through the least-crowded BB chip as an intermediary:
//
//   CHIP_I: close X(n1) ↔ Y(bb_chip)   → n1 on bb_chip X-bus
//   CHIP_J: close X(n2) ↔ Y(bb_chip)   → n2 on same bb_chip X-bus
//   (the two X lines on the BB chip that go to I and J are separate traces,
//    so no BB rows are touched — only the bus wires are used as intermediary)
//
//   Wait, that still leaves the two traces unconnected on the BB chip side.
//   The final bridge step is:
//   BB chip: close X(CHIP_I bus) ↔ Xany — but X-to-X isn't possible.
//   Instead, pick a free Y on the BB chip to bridge the two X bus lines:
//   BB chip: close X(c0 bus) ↔ Yfree AND X(c1 bus) ↔ Yfree (same Y).
//
//   Full 4-command sequence:
//   CHIP_I (c0): X(n1) ↔ Y(bb)        → n1 on I-to-bb bus
//   CHIP_J (c1): X(n2) ↔ Y(bb)        → n2 on J-to-bb bus
//   BB chip:     X(bus_to_I) ↔ Yfree
//   BB chip:     X(bus_to_J) ↔ Yfree  ← same Yfree, bridges the two bus lines
// ---------------------------------------------------------------------------
void resolveAltPaths()
{
    for (int i = 0; i < numberOfPaths; i++) {
        if (!path[i].altPathNeeded || path[i].skip) continue;

        const int c0  = path[i].chip[0];
        const int c1  = path[i].chip[1];
        const int n1  = path[i].node1;
        const int n2  = path[i].node2;
        const int net = path[i].net;

        switch (path[i].pathType) {

        // ── NANOtoNANO / EXTtoEXT / NANOtoEXT across two SF chips ────────────
        case NANOtoNANO:
        case EXTtoEXT:
        case NANOtoEXT:
        case NANOtoSF:
        case EXTtoSF:
        case SFtoSF:
        {
            // Pick the least-crowded BB chip as the intermediary bridge.
            int bbChip = -1, minConn = 9999;
            for (int c = CHIP_A; c <= CHIP_H; c++) {
                int conn = 0;
                for (int x = 0; x < 16; x++) if (ch[c].xStatus[x] != -1) conn++;
                if (conn < minConn) { minConn = conn; bbChip = c; }
            }
            if (bbChip == -1) { path[i].skip = true; break; }

            // X index for c0 bus and c1 bus on the BB chip
            int x_bb_c0 = xIndexForNodeOnChip(c0, bbChip, 0);
            int x_bb_c1 = xIndexForNodeOnChip(c1, bbChip, 0);
            // Free Y on the BB chip (will act as the bridging wire)
            int y_bridge = findFreeYOnChip(bbChip);
            // X indices for n1 on c0 and n2 on c1
            int x0 = resolveXForNode(n1, c0, path[i].nodeType[0]);
            int x1 = resolveXForNode(n2, c1, path[i].nodeType[1]);
            // Y index for the BB chip on c0 and c1
            int y0_sf = yIndexForNodeOnChip(bbChip, c0);
            int y1_sf = yIndexForNodeOnChip(bbChip, c1);

            if (x_bb_c0==-1 || x_bb_c1==-1 || y_bridge==-1 ||
                x0==-1 || x1==-1 || y0_sf==-1 || y1_sf==-1) {
                path[i].skip = true; break;
            }

            // 4 switch commands across 3 chips:
            path[i].chip[0] = c0;     path[i].x[0] = x0;      path[i].y[0] = y0_sf;
            path[i].chip[1] = c1;     path[i].x[1] = x1;      path[i].y[1] = y1_sf;
            path[i].chip[2] = bbChip; path[i].x[2] = x_bb_c0; path[i].y[2] = y_bridge;
            path[i].chip[3] = bbChip; path[i].x[3] = x_bb_c1; path[i].y[3] = y_bridge;

            ch[c0].xStatus[x0]          = (int16_t)net;
            ch[c1].xStatus[x1]          = (int16_t)net;
            ch[bbChip].xStatus[x_bb_c0] = (int16_t)net;
            ch[bbChip].xStatus[x_bb_c1] = (int16_t)net;
            ch[bbChip].yStatus[y_bridge] = (int16_t)net;
            path[i].altPathNeeded = 0;
        }
        break;

        default:
            // Other alt-path types not yet implemented — leave flagged.
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Stage 7: addParallelConnections
//
// For every BBtoBB path that only used chip[0]/chip[1], try to fill
// chip[2]/chip[3] with a second parallel switch path, halving Ron:
//
//   Same-chip  — find any free X on the same chip and connect it to the
//                same two Y rows already in use.  Result: two X lines share
//                the current, each path = 2×Ron → combined = Ron.
//
//   Cross-chip — each inter-chip bus has two lanes in the xMap (the two
//                duplicate entries, e.g. CHIP_B,CHIP_B in Chip A's xMap).
//                Lane 0 is used by commitPaths(); lane 1 is added here if
//                it is still free.  Same effect: Ron halved per chip pair.
//
// sendPath() already iterates chip[0..3], so no changes needed there.
// If resources are unavailable the path is left as-is (graceful skip).
// ---------------------------------------------------------------------------
void addParallelConnections()
{
    for (int i = 0; i < numberOfPaths; i++) {
        if (path[i].skip) continue;

        switch (path[i].pathType) {

        // ── BBtoBB: fill chip[2]/chip[3] ─────────────────────────────────────
        case BBtoBB: {
            if (path[i].chip[2] != -1) break; // slots already used (alt path)

            if (path[i].sameChip) {
                // Same-chip: add a 2nd free X bridging the same two Y rows.
                // Before: 2×Ron.  After: Ron.
                int c  = path[i].chip[0];
                int y0 = path[i].y[0];
                int y1 = path[i].y[1];
                int x2 = findFreeXOnChip(c);
                if (x2 == -1) break;
                path[i].chip[2] = c;  path[i].x[2] = x2;  path[i].y[2] = y0;
                path[i].chip[3] = c;  path[i].x[3] = x2;  path[i].y[3] = y1;
                ch[c].xStatus[x2] = (int16_t)path[i].net;

            } else {
                // Cross-chip: use lane 1 of the inter-chip bus (if free).
                // Before: 2×Ron.  After: Ron.
                int c0  = path[i].chip[0];
                int c1  = path[i].chip[1];
                int y0  = path[i].y[0];
                int y1  = path[i].y[1];
                int x0b = xIndexForNodeOnChip(c1, c0, 1); // lane 1 on c0→c1
                int x1b = xIndexForNodeOnChip(c0, c1, 1); // lane 1 on c1→c0
                if (x0b == -1 || x1b == -1)              break;
                if (ch[c0].xStatus[x0b] != -1)           break;
                if (ch[c1].xStatus[x1b] != -1)           break;
                path[i].chip[2] = c0; path[i].x[2] = x0b; path[i].y[2] = y0;
                path[i].chip[3] = c1; path[i].x[3] = x1b; path[i].y[3] = y1;
                ch[c0].xStatus[x0b] = (int16_t)path[i].net;
                ch[c1].xStatus[x1b] = (int16_t)path[i].net;
            }
            break;
        }

        // ── BBtoBBL: fill chip[3]/chip[4] (BB side only) ─────────────────────
        // Path structure:
        //   chip[0]=c0, x[0]=x_bb,  y[0]=y(n1)       — n1 row  → X bus
        //   chip[1]=c0, x[1]=x_bb,  y[1]=y(CHIP_L)   — X bus   → ChipL bus
        //   chip[2]=L,  x[2]=x(n2), y[2]=y(c0)        — ChipL switch
        //
        // Chip L's node has only one physical X trace, so it can't be doubled.
        // Adding x_bb2 on c0 halves the BB-chip contribution:
        //   Before: 3×Ron ≈ 150Ω.  After: 2×Ron ≈ 100Ω.
        case BBtoBBL: {
            if (path[i].chip[3] != -1) break; // slots already used
            int c0   = path[i].chip[0];
            int y_n1 = path[i].y[0];  // Y index of regular node on c0
            int y_L  = path[i].y[1];  // Y index of CHIP_L bus on c0
            int x_bb2 = findFreeXOnChip(c0);
            if (x_bb2 == -1) break;
            path[i].chip[3] = c0; path[i].x[3] = x_bb2; path[i].y[3] = y_n1;
            path[i].chip[4] = c0; path[i].x[4] = x_bb2; path[i].y[4] = y_L;
            ch[c0].xStatus[x_bb2] = (int16_t)path[i].net;
            break;
        }

        default:
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// Full pipeline including commit, alt-path resolution, and parallel lowering
// ---------------------------------------------------------------------------
void netsToChipConnectionsFull()
{
    bridgesToPaths();
    findStartAndEndChips();
    assignPathType();
    resolveChipCandidates();
    commitPaths();
    resolveAltPaths();
    addParallelConnections();
}
