#include "jz_debug.h"
#include "path_mapping_algo.h"
#include "nets_to_chip_connections.h"
#include "pin_map.h"

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

static const char *chipName(int c)
{
    static const char *names[] = {"A","B","C","D","E","F","G","H","I","J","K","L"};
    if (c >= 0 && c < 12) return names[c];
    return "?";
}

static const char *pathTypeName(pathType t)
{
    switch (t) {
        case BBtoBB:    return "BB-BB";
        case BBtoNANO:  return "BB-NANO";
        case NANOtoNANO:return "NANO-NANO";
        case BBtoSF:    return "BB-SF";
        case NANOtoSF:  return "NANO-SF";
        case BBtoBBL:   return "BB-BBL";
        case NANOtoBBL: return "NANO-BBL";
        case SFtoSF:    return "SF-SF";
        case SFtoBBL:   return "SF-BBL";
        case BBLtoBBL:  return "BBL-BBL";
        case BBtoEXT:   return "BB-EXT";
        case NANOtoEXT: return "NANO-EXT";
        case EXTtoSF:   return "EXT-SF";
        case EXTtoEXT:  return "EXT-EXT";
        case EXTtoBBL:  return "EXT-BBL";
        default:        return "UNKNOWN";
    }
}

// Convert a logical node number to a short human-readable label.
// Buffer must be at least 12 bytes.
static void nodeLabel(int n, char *buf)
{
    if (n == -1)                    { strcpy(buf, "-"); return; }
    if (n >= TOP_1    && n <= TOP_30)   { snprintf(buf, 12, "TOP_%d",    n);           return; }
    if (n >= BOTTOM_1 && n <= BOTTOM_30){ snprintf(buf, 12, "BOT_%d",    n - 30);      return; }
    if (n >= NANO_D0  && n <= NANO_D13) { snprintf(buf, 12, "NANO_D%d",  n - NANO_D0); return; }
    if (n == NANO_RESET)                { strcpy(buf, "NANO_RST");  return; }
    if (n == NANO_AREF)                 { strcpy(buf, "NANO_AREF"); return; }
    if (n >= NANO_A0  && n <= NANO_A7)  { snprintf(buf, 12, "NANO_A%d",  n - NANO_A0); return; }
    if (n == GND)                       { strcpy(buf, "GND");       return; }
    if (n == SUPPLY_5V)                 { strcpy(buf, "+5V");       return; }
    if (n == SUPPLY_3V3)                { strcpy(buf, "+3.3V");     return; }
    if (n == DAC0)                      { strcpy(buf, "DAC0");      return; }
    if (n == DAC1)                      { strcpy(buf, "DAC1");      return; }
    if (n == ADC0)                      { strcpy(buf, "ADC0");      return; }
    if (n == ADC1)                      { strcpy(buf, "ADC1");      return; }
    if (n == ADC2)                      { strcpy(buf, "ADC2");      return; }
    if (n == ADC3)                      { strcpy(buf, "ADC3");      return; }
    if (n == ISENSE_PLUS)               { strcpy(buf, "ISENSE+");   return; }
    if (n == ISENSE_MINUS)              { strcpy(buf, "ISENSE-");   return; }
    if (n == ESP_REST)                  { strcpy(buf, "ESP_RST");   return; }
    if (n == RP_UART_TX)                { strcpy(buf, "RP_TX");     return; }
    if (n == RP_UART_RX)                { strcpy(buf, "RP_RX");     return; }
    if (n == EMPTY_NET)                 { strcpy(buf, "EMPTY");     return; }
    if (n >= EXT_PIN_1 && n <= 169)     { snprintf(buf, 12, "EXT_%d", n - EXT_PIN_1 + 1); return; }
    snprintf(buf, 12, "NODE_%d", n);
}

// ---------------------------------------------------------------------------
// printChipSummary — one line per chip
// ---------------------------------------------------------------------------
void JZDebug::printChipSummary(Stream &out)
{
    out.println(F("\n=== CHIP SUMMARY ==="));
    out.println(F("Chip | Active X pins                   | Active Y buses"));
    out.println(F("-----|----------------------------------|---------------"));

    for (int c = 0; c < 12; c++) {
        int xCount = 0, yCount = 0;
        char xList[80] = "";
        char yList[40] = "";

        for (int x = 0; x < 16; x++) {
            if (ch[c].xStatus[x] != -1) {
                xCount++;
                char tmp[8];
                snprintf(tmp, sizeof(tmp), "X%d ", x);
                strncat(xList, tmp, sizeof(xList) - strlen(xList) - 1);
            }
        }
        for (int y = 0; y < 8; y++) {
            if (ch[c].yStatus[y] != -1) {
                yCount++;
                char tmp[8];
                snprintf(tmp, sizeof(tmp), "Y%d ", y);
                strncat(yList, tmp, sizeof(yList) - strlen(yList) - 1);
            }
        }

        if (xCount == 0 && yCount == 0) {
            out.printf("  %s  | (idle)                           | (idle)\r\n", chipName(c));
        } else {
            out.printf("  %s  | %-32s | %s\r\n", chipName(c), xList, yList);
        }
    }
}

// ---------------------------------------------------------------------------
// printChipMap — X/Y crosspoint grid per chip
// ---------------------------------------------------------------------------
void JZDebug::printChipMap(Stream &out)
{
    out.println(F("\n=== CHIP CROSSPOINT MAP ==="));
    out.println(F("  '1' = closed  '.' = open  '-' = not monitored by xStatus"));

    for (int c = 0; c < 12; c++) {
        // Count active crosspoints
        int active = 0;
        for (int x = 0; x < 16; x++)
            if (ch[c].xStatus[x] != -1) active++;

        out.printf("\n-- Chip %s (index %d) -- %d active X pin(s) --\r\n",
                   chipName(c), c, active);

        // Header row: X indices
        out.print(F("     "));
        for (int x = 0; x < 16; x++) out.printf("X%-2d ", x);
        out.println();
        out.print(F("     "));
        for (int x = 0; x < 16; x++) out.print(F("--- "));
        out.println();

        // One row per Y bus
        for (int y = 0; y < 8; y++) {
            char yLabel[16];
            // Show what this Y maps to
            int ym = ch[c].yMap[y];
            char nodeBuf[12];
            nodeLabel(ym, nodeBuf);
            out.printf("Y%d %-7s", y, nodeBuf);

            for (int x = 0; x < 16; x++) {
                // xStatus == -1 means idle/not connected at this X
                // We show '1' if xStatus[x] > 0 AND we are in this Y row.
                // Since xStatus only tracks per-X (not per-X-Y intersection),
                // we mark the X column that's active on this chip.
                char cell = '.';
                if (ch[c].xStatus[x] != -1) {
                    // Check if any path uses this chip at this X with this Y
                    for (int p = 0; p < numberOfPaths; p++) {
                        for (int hop = 0; hop < 6; hop++) {
                            if (path[p].chip[hop] == c &&
                                path[p].x[hop]    == x &&
                                path[p].y[hop]    == y) {
                                cell = '1';
                                break;
                            }
                        }
                        if (cell == '1') break;
                    }
                }
                out.printf(" %c  ", cell);
            }
            out.println();
        }

        // Show X map row (what each X pin connects to)
        out.print(F("  XM: "));
        for (int x = 0; x < 16; x++) {
            char buf[12];
            nodeLabel(ch[c].xMap[x], buf);
            out.printf("%-4s", buf);
        }
        out.println();
    }
}

// ---------------------------------------------------------------------------
// printPaths — all paths in path[]
// ---------------------------------------------------------------------------
void JZDebug::printPaths(Stream &out)
{
    out.println(F("\n=== ACTIVE PATHS ==="));
    out.printf("Total paths: %d\r\n", numberOfPaths);

    if (numberOfPaths == 0) {
        out.println(F("  (no active paths)"));
        return;
    }

    for (int i = 0; i < numberOfPaths; i++) {
        pathStruct &p = path[i];
        if (p.skip) {
            out.printf("  [%3d] SKIPPED\r\n", i);
            continue;
        }

        char n1[12], n2[12];
        nodeLabel(p.node1, n1);
        nodeLabel(p.node2, n2);

        out.printf("  [%3d] Net%d  %-10s -> %-10s  type=%-10s  sameChip=%d  Lchip=%d\r\n",
                   i, p.net, n1, n2, pathTypeName(p.pathType),
                   (int)p.sameChip, (int)p.Lchip);

        // Print hops
        for (int hop = 0; hop < 6; hop++) {
            if (p.chip[hop] == -1) break;
            out.printf("         hop%d: Chip%s  X=%2d  Y=%2d\r\n",
                       hop, chipName(p.chip[hop]), p.x[hop], p.y[hop]);
        }

        if (p.altPathNeeded) out.println(F("         (alt path needed)"));
        if (p.duplicate)     out.printf("         (duplicate=%d)\r\n", p.duplicate);
    }
}

// ---------------------------------------------------------------------------
// printNets — configured nets
// ---------------------------------------------------------------------------
void JZDebug::printNets(Stream &out)
{
    out.println(F("\n=== NETS ==="));

    int printed = 0;
    for (int i = 0; i < MAX_NETS; i++) {
        netStruct &n = net[i];
        if (n.number == 127) continue;  // Empty net sentinel

        // Count non-empty nodes
        int nodeCount = 0;
        for (int j = 0; j < MAX_NODES; j++) {
            if (n.nodes[j] == 0 || n.nodes[j] == EMPTY_NET) break;
            nodeCount++;
        }
        if (nodeCount == 0 && n.specialFunction == -1) continue;

        out.printf("  Net[%3d] #%3d  %-14s  color=#%06lX  SF=%d  nodes=%d: ",
                   i, (int)n.number,
                   n.name ? n.name : "?",
                   (unsigned long)n.rawColor,
                   (int)n.specialFunction,
                   nodeCount);

        for (int j = 0; j < nodeCount && j < MAX_NODES; j++) {
            char buf[12];
            nodeLabel(n.nodes[j], buf);
            out.printf("%s ", buf);
        }
        out.println();
        printed++;
    }

    if (printed == 0) out.println(F("  (no nets configured)"));
}

// ---------------------------------------------------------------------------
// printAll
// ---------------------------------------------------------------------------
void JZDebug::printAll(Stream &out)
{
    out.println(F("\n========================================"));
    out.println(F("         JumperZ Debug Dump"));
    out.println(F("========================================"));
    printChipSummary(out);
    printPaths(out);
    printNets(out);
    printChipMap(out);
    out.println(F("\n========================================"));
    out.println(F("         End of Debug Dump"));
    out.println(F("========================================\n"));
}
