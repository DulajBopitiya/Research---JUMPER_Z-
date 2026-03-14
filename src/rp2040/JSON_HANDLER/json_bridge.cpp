#include "json_bridge.h"
#include "jz_debug.h"

namespace JsonBridge
{
  // ── Internal helpers ──────────────────────────────────────────────────────

  // Map a logical node number to an LED strip index (best-effort).
  // TOP_1..TOP_30   → M1 row 0, col 0-29
  // BOTTOM_1..BOTTOM_30 → M2 row 0, col 0-29
  // Everything else → -1 (no LED representation yet)
  static int nodeToLedIndex(int node)
  {
    if (node >= TOP_1 && node <= TOP_30)
      return (int)LedMatrix::mid1Index(0, (uint8_t)(node - TOP_1));
    if (node >= BOTTOM_1 && node <= BOTTOM_30)
      return (int)LedMatrix::mid2Index(0, (uint8_t)(node - BOTTOM_1));
    return -1;
  }

  // Look up a node name string in sfMappings[]. Returns node number or -1.
  static int resolveNodeName(const char *name)
  {
    if (!name || name[0] == '\0') return -1;
    for (int i = 0; i < 200; i++) {
      if (sfMappings[i].name == nullptr) break;
      if (!strcmp(sfMappings[i].name, name)) return sfMappings[i].replacement;
    }
    return -1;
  }

  // Reset all user-defined nets (indices 8+) to empty.
  // Pre-defined special nets (0-7: GND, 5V, 3.3V, DAC0, DAC1, ISense+/-)
  // are never touched.
  static void clearUserNets()
  {
    for (int n = 8; n < MAX_NETS; n++) {
      net[n].number = (uint8_t)n;
      for (int i = 0; i < MAX_NODES; i++) {
        net[n].nodes[i]       = 0;
        net[n].bridges[i][0]  = 0;
        net[n].bridges[i][1]  = 0;
      }
      net[n].specialFunction   = -1;
      net[n].machine           = true;
      net[n].numberOfDuplicates = 0;
    }
  }

  // Add a user net. nodes[] has numNodes entries. Creates chain bridges:
  //   nodes[0]↔nodes[1], nodes[1]↔nodes[2], …
  // Returns the net index used, or -1 if all slots are full.
  static int addUserNet(int *nodes, int numNodes,
                        LedMatrix::RGB color, uint32_t rawCol)
  {
    for (int n = 8; n < MAX_NETS; n++) {
      if (net[n].nodes[0] != 0) continue; // slot in use
      net[n].number        = (uint8_t)n;
      net[n].color         = color;
      net[n].rawColor      = rawCol;
      net[n].machine       = true;
      net[n].specialFunction = -1;

      int nodeCount = (numNodes < MAX_NODES - 1) ? numNodes : MAX_NODES - 1;
      for (int i = 0; i < nodeCount; i++)
        net[n].nodes[i] = (int16_t)nodes[i];

      // Chain bridges: (0,1), (1,2), (2,3) …
      int bi = 0;
      for (int i = 0; i < nodeCount - 1 && bi < MAX_NODES; i++) {
        net[n].bridges[bi][0] = (int16_t)nodes[i];
        net[n].bridges[bi][1] = (int16_t)nodes[i + 1];
        bi++;
      }
      return n;
    }
    return -1;
  }
  // ---------------- helpers ----------------
  static void sendJson(Stream &s, JsonDocument &doc)
  {
    serializeJson(doc, s);
    s.print('\n');
  }

  // ---------------- public API ----------------
  void begin(Adafruit_NeoPixel &strip)
  {
    (void)strip; // strip is owned by LedMatrix; kept for compatibility.
    LedMatrix::frameClear();
    LedMatrix::frameResetBlink();
  }

  void clearFrame()
  {
    LedMatrix::frameClear();
  }

  void clear()
  {
    // Clear LEDs
    LedMatrix::frameClear();
    LedMatrix::clear();
    LedMatrix::show();
    // Clear all CH446Q connections and user nets
    clearAllChips();
    clearUserNets();
    numberOfPaths = 0;
  }

  void tick()
  {
    LedMatrix::frameTick();
  }

  void handle(Stream &replyTo, JsonDocument &req)
  {
    const char *cmd = req["cmd"] | "";
    JsonDocument resp;

    if (!strcmp(cmd, "ping"))
    {
      resp["ok"] = true;
      resp["fw"] = "rp2040-ledmatrix-bridge-blink";
      resp["leds"] = (int)LedMatrix::NUM_LEDS;
      resp["blink_ms"] = (int)LedMatrix::BLINK_PERIOD_MS;
      sendJson(replyTo, resp);
      return;
    }

    if (!strcmp(cmd, "clear"))
    {
      clear();
      resp["ok"] = true;
      sendJson(replyTo, resp);
      return;
    }

    if (!strcmp(cmd, "wokwi_wires"))
    {
      if (!req["wires"].is<JsonArray>())
      {
        resp["ok"] = false;
        resp["err"] = "missing wires[]";
        sendJson(replyTo, resp);
        return;
      }

      LedMatrix::frameClear();
      LedMatrix::frameResetBlink();

      JsonArray wires = req["wires"].as<JsonArray>();
      int pathPainted = 0;
      int endpointsMarked = 0;

      for (JsonVariant wv : wires)
      {
        JsonObject wire = wv.as<JsonObject>();
        const char *cname = wire["color"] | "";
        LedMatrix::RGB col = LedMatrix::wokwiColorToRgb(cname);

        // If python provides points -> paint full path
        if (wire["points"].is<JsonArray>())
        {
          JsonArray pts = wire["points"].as<JsonArray>();

          int firstIdx = -1;
          int lastIdx = -1;

          for (JsonVariant pv : pts)
          {
            if (!pv.is<JsonArray>()) continue;
            JsonArray p = pv.as<JsonArray>();
            if (p.size() < 3) continue;

            const char *sec = p[0] | "";
            int row = p[1] | -1;
            int coln = p[2] | -1;

            int idx = LedMatrix::logicalToIndex(sec, row, coln);
            if (idx < 0) continue;

            if (firstIdx < 0) firstIdx = idx;
            lastIdx = idx;

            LedMatrix::framePaintPathIdx(idx, col);
            pathPainted++;
          }

          if (firstIdx >= 0) { LedMatrix::frameMarkEndpointIdx(firstIdx, col); endpointsMarked++; }
          if (lastIdx >= 0)  { LedMatrix::frameMarkEndpointIdx(lastIdx, col); endpointsMarked++; }

          continue;
        }

        // Otherwise: only endpoints a/b exist
        JsonArray a = wire["a"].as<JsonArray>();
        JsonArray b = wire["b"].as<JsonArray>();
        if (a.size() < 3 || b.size() < 3) continue;

        int idxA = LedMatrix::logicalToIndex(a[0] | "", a[1] | -1, a[2] | -1);
        int idxB = LedMatrix::logicalToIndex(b[0] | "", b[1] | -1, b[2] | -1);

        if (idxA >= 0)
        {
          LedMatrix::framePaintPathIdx(idxA, col); pathPainted++;
          LedMatrix::frameMarkEndpointIdx(idxA, col); endpointsMarked++;
        }

        if (idxB >= 0)
        {
          LedMatrix::framePaintPathIdx(idxB, col); pathPainted++;
          LedMatrix::frameMarkEndpointIdx(idxB, col); endpointsMarked++;
        }
      }

      LedMatrix::frameApplyFull();

      resp["ok"] = true;
      resp["path_leds"] = pathPainted;
      resp["endpoints"] = endpointsMarked;
      resp["blink_ms"] = (int)LedMatrix::BLINK_PERIOD_MS;
      resp["note"] = "Endpoints blink; path stays steady";
      sendJson(replyTo, resp);
      return;
    }

    // ── connect ──────────────────────────────────────────────────────────────
    // Close physical CH446Q switches and light endpoint LEDs.
    //
    // Request:
    //   {
    //     "cmd": "connect",
    //     "nets": [
    //       { "nodes": ["NANO_D3","TOP_5"], "color": "#00FF00" },
    //       { "nodes": ["GND","BOTTOM_10","BOTTOM_11"], "color": "blue" }
    //     ]
    //   }
    //
    // Each entry creates one net. Nodes are string names looked up via
    // sfMappings[]. At least 2 nodes are required per net entry.
    // Bridges are chained: (nodes[0]↔nodes[1]), (nodes[1]↔nodes[2]) …
    //
    // NOTE: every "connect" call is a full re-program — it clears all
    // previous user connections before applying the new set.
    //
    // Response:
    //   { "ok": true, "nets_added": 2, "paths": 4,
    //     "skipped": 1, "err_nodes": ["BADNAME"] }
    if (!strcmp(cmd, "connect"))
    {
      if (!req["nets"].is<JsonArray>())
      {
        resp["ok"]  = false;
        resp["err"] = "missing nets[]";
        sendJson(replyTo, resp);
        return;
      }

      // Full re-program: clear previous user connections
      clearAllChips();
      clearUserNets();
      numberOfPaths = 0;
      LedMatrix::frameClear();
      LedMatrix::frameResetBlink();

      JsonArray netsArr = req["nets"].as<JsonArray>();
      int netsAdded  = 0;
      int skipped    = 0;

      JsonDocument errDoc;
      JsonArray    errNodes = errDoc.to<JsonArray>();

      for (JsonVariant nv : netsArr)
      {
        JsonObject netObj = nv.as<JsonObject>();
        if (!netObj["nodes"].is<JsonArray>()) { skipped++; continue; }

        // Resolve node name strings → node numbers
        JsonArray nameArr = netObj["nodes"].as<JsonArray>();
        int resolvedNodes[MAX_NODES];
        int resolvedCount = 0;

        for (JsonVariant nameVar : nameArr)
        {
          const char *name = nameVar | "";
          int nodeNum = resolveNodeName(name);
          if (nodeNum < 0) {
            errNodes.add(name);
            continue;
          }
          if (resolvedCount < MAX_NODES) resolvedNodes[resolvedCount++] = nodeNum;
        }

        if (resolvedCount < 2) { skipped++; continue; } // need at least 2 nodes

        // Parse color (hex string "#RRGGBB" or Wokwi name)
        const char   *colorStr = netObj["color"] | "#FFFFFF";
        LedMatrix::RGB_t col   = LedMatrix::wokwiColorToRgb(colorStr);
        uint32_t rawCol = ((uint32_t)col.r << 16) | ((uint32_t)col.g << 8) | col.b;

        int netIdx = addUserNet(resolvedNodes, resolvedCount, col, rawCol);
        if (netIdx < 0) { skipped++; continue; }

        // Light endpoint LEDs for this net
        // (Intermediate path LEDs are left to wokwi_wires; here we just mark
        //  the two endpoint nodes so the user sees which nodes are connected.)
        int ledA = nodeToLedIndex(resolvedNodes[0]);
        int ledB = nodeToLedIndex(resolvedNodes[resolvedCount - 1]);
        if (ledA >= 0) LedMatrix::frameMarkEndpointIdx(ledA, col);
        if (ledB >= 0) LedMatrix::frameMarkEndpointIdx(ledB, col);

        netsAdded++;
      }

      // Run the full path-mapping pipeline and push to CH446Q
      netsToChipConnectionsFull();
      sendAllPaths(1);

      LedMatrix::frameApplyFull();

      resp["ok"]         = true;
      resp["nets_added"] = netsAdded;
      resp["paths"]      = numberOfPaths;
      resp["skipped"]    = skipped;
      if (errNodes.size() > 0) resp["err_nodes"] = errNodes;
      sendJson(replyTo, resp);
      return;
    }

    // ── netlist_query ─────────────────────────────────────────────────────────
    // Return a summary of the current committed paths (read-only).
    //
    // Response:
    //   { "ok": true, "paths": 3,
    //     "list": [
    //       { "i":0, "net":8, "type":3, "n1":73, "n2":5,
    //         "c0":0, "c1":8, "x0":0, "y0":4, "x1":3, "y1":0 },
    //       …
    //     ]}
    if (!strcmp(cmd, "netlist_query"))
    {
      resp["ok"]    = true;
      resp["paths"] = numberOfPaths;
      JsonArray list = resp["list"].to<JsonArray>();
      for (int i = 0; i < numberOfPaths && i < 32; i++) // cap at 32 to keep JSON small
      {
        if (path[i].skip) continue;
        JsonObject p = list.add<JsonObject>();
        p["i"]    = i;
        p["net"]  = path[i].net;
        p["type"] = (int)path[i].pathType;
        p["n1"]   = path[i].node1;
        p["n2"]   = path[i].node2;
        p["c0"]   = path[i].chip[0];
        p["c1"]   = path[i].chip[1];
        p["x0"]   = path[i].x[0];
        p["y0"]   = path[i].y[0];
        p["x1"]   = path[i].x[1];
        p["y1"]   = path[i].y[1];
        if (path[i].altPathNeeded) p["alt"] = 1;
      }
      sendJson(replyTo, resp);
      return;
    }

    // ── debug ─────────────────────────────────────────────────────────────────
    // Dump chip map, paths, and nets back to the caller (replyTo).
    // Text lines are sent first, then a final JSON ACK line.
    //
    //   {"cmd":"debug"}                  → full dump (chips + paths + nets)
    //   {"cmd":"debug","what":"chips"}   → chip summary + crosspoint grid
    //   {"cmd":"debug","what":"paths"}   → active paths only
    //   {"cmd":"debug","what":"nets"}    → nets only
    //   {"cmd":"debug","what":"summary"} → chip summary one-liner only
    if (!strcmp(cmd, "debug"))
    {
      const char *what = req["what"] | "all";
      if      (!strcmp(what, "chips"))   { JZDebug::printChipSummary(replyTo); JZDebug::printChipMap(replyTo); }
      else if (!strcmp(what, "paths"))     JZDebug::printPaths(replyTo);
      else if (!strcmp(what, "nets"))      JZDebug::printNets(replyTo);
      else if (!strcmp(what, "summary"))   JZDebug::printChipSummary(replyTo);
      else                                 JZDebug::printAll(replyTo);

      resp["ok"]   = true;
      resp["what"] = what;
      sendJson(replyTo, resp);
      return;
    }

    resp["ok"] = false;
    resp["err"] = "unknown cmd";
    resp["cmd"] = cmd;
    sendJson(replyTo, resp);
  }
}