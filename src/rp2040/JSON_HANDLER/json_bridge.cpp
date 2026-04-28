#include "json_bridge.h"
#include "jz_debug.h"
#include "measurements.h"
#include "JumperZ_SEQ.h"

namespace JsonBridge
{
  // Tracks which net[] slots the last measure command occupied so they can
  // be freed on the next call or on measure_clear.
  static int s_measNetIdx[3] = {-1, -1, -1};   // [0]=node, [1]=plus/ref, [2]=ref→GND

  // Tracks which net[] slots the most recent probe_connect command occupied,
  // so successive probe_connect calls replace probe routing without piling
  // up duplicates and without disturbing other user nets.
  static constexpr int PROBE_NET_SLOTS = 16;
  static int s_probeNetIdx[PROBE_NET_SLOTS] = {
      -1, -1, -1, -1, -1, -1, -1, -1,
      -1, -1, -1, -1, -1, -1, -1, -1
  };

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

  // Paint the visual LED path for one bridge (n1 ↔ n2) on the framebuffer.
  //
  // TOP_A ↔ TOP_B  (M1 → M1):
  //   Horizontal line at row 0, cols A..B.
  //
  // BOTTOM_A ↔ BOTTOM_B  (M2 → M2):
  //   Horizontal line at row 0, cols A..B.
  //
  // TOP_A ↔ BOTTOM_B  (M1 → M2 cross-section):
  //   • M1 rows 3–4 at col A  (wire exits M1 downward)
  //   • M2 rows 0–1 at col A  (wire enters M2 at the same column)
  //   • M2 row 1, cols A..B   (horizontal routing to destination)
  //   • M2 row 0 at col B     (destination column)
  //
  // Non-breadboard nodes (GND, 5V, NANO, etc.) just get an endpoint marker
  // where they have a LED representation.
  //
  // Endpoint blink markers are always placed on the outermost row-0 LEDs of
  // the connected columns.
  static void paintBridgeLeds(int n1, int n2, LedMatrix::RGB_t col)
  {
    bool isTop1 = (n1 >= TOP_1    && n1 <= TOP_30);
    bool isTop2 = (n2 >= TOP_1    && n2 <= TOP_30);
    bool isBot1 = (n1 >= BOTTOM_1 && n1 <= BOTTOM_30);
    bool isBot2 = (n2 >= BOTTOM_1 && n2 <= BOTTOM_30);

    if (isTop1 && isTop2) {
      // ── M1 → M1: horizontal path at row 0 ──────────────────────────────
      uint8_t c1 = (uint8_t)(n1 - TOP_1), c2 = (uint8_t)(n2 - TOP_1);
      uint8_t lo = c1 < c2 ? c1 : c2, hi = c1 > c2 ? c1 : c2;
      for (uint8_t c = lo; c <= hi; c++)
        LedMatrix::framePaintPathIdx(LedMatrix::mid1Index(0, c), col);
      LedMatrix::frameMarkEndpointIdx(LedMatrix::mid1Index(0, c1), col);
      LedMatrix::frameMarkEndpointIdx(LedMatrix::mid1Index(0, c2), col);
    }
    else if (isBot1 && isBot2) {
      // ── M2 → M2: horizontal path at row 0 ──────────────────────────────
      uint8_t c1 = (uint8_t)(n1 - BOTTOM_1), c2 = (uint8_t)(n2 - BOTTOM_1);
      uint8_t lo = c1 < c2 ? c1 : c2, hi = c1 > c2 ? c1 : c2;
      for (uint8_t c = lo; c <= hi; c++)
        LedMatrix::framePaintPathIdx(LedMatrix::mid2Index(0, c), col);
      LedMatrix::frameMarkEndpointIdx(LedMatrix::mid2Index(0, c1), col);
      LedMatrix::frameMarkEndpointIdx(LedMatrix::mid2Index(0, c2), col);
    }
    else if ((isTop1 && isBot2) || (isBot1 && isTop2)) {
      // ── M1 ↔ M2 cross-section path ──────────────────────────────────────
      uint8_t cTop = isTop1 ? (uint8_t)(n1 - TOP_1)    : (uint8_t)(n2 - TOP_1);
      uint8_t cBot = isBot2 ? (uint8_t)(n2 - BOTTOM_1) : (uint8_t)(n1 - BOTTOM_1);

      // M1: exit rows 3, 4 at cTop
      LedMatrix::framePaintPathIdx(LedMatrix::mid1Index(3, cTop), col);
      LedMatrix::framePaintPathIdx(LedMatrix::mid1Index(4, cTop), col);

      // M2: entry rows 0, 1 at cTop (drops into M2 at the same column)
      LedMatrix::framePaintPathIdx(LedMatrix::mid2Index(0, cTop), col);
      LedMatrix::framePaintPathIdx(LedMatrix::mid2Index(1, cTop), col);

      // M2: horizontal routing at row 1 from cTop to cBot
      uint8_t lo = cTop < cBot ? cTop : cBot;
      uint8_t hi = cTop > cBot ? cTop : cBot;
      for (uint8_t c = lo; c <= hi; c++)
        LedMatrix::framePaintPathIdx(LedMatrix::mid2Index(1, c), col);

      // M2: ensure row 0 at cBot is painted (destination endpoint column)
      LedMatrix::framePaintPathIdx(LedMatrix::mid2Index(0, cBot), col);

      // Endpoint blink markers
      LedMatrix::frameMarkEndpointIdx(LedMatrix::mid1Index(0, cTop), col);
      LedMatrix::frameMarkEndpointIdx(LedMatrix::mid2Index(0, cBot), col);
    }
    else {
      // ── Non-breadboard node(s): fall back to endpoint-only ───────────────
      int led1 = nodeToLedIndex(n1);
      int led2 = nodeToLedIndex(n2);
      if (led1 >= 0) LedMatrix::frameMarkEndpointIdx(led1, col);
      if (led2 >= 0) LedMatrix::frameMarkEndpointIdx(led2, col);
    }
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
  // Free one user net slot back to empty.
  static void clearNetSlot(int n)
  {
    if (n < 8 || n >= MAX_NETS) return;
    net[n].number = (uint8_t)n;
    for (int i = 0; i < MAX_NODES; i++) {
      net[n].nodes[i]      = 0;
      net[n].bridges[i][0] = 0;
      net[n].bridges[i][1] = 0;
    }
    net[n].specialFunction    = -1;
    net[n].machine            = true;
    net[n].numberOfDuplicates = 0;
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
    // Forget any tracked probe slots — they were just zeroed out.
    for (int i = 0; i < PROBE_NET_SLOTS; i++) s_probeNetIdx[i] = -1;
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
      // Forget any tracked probe slots — clearUserNets() just emptied them.
      for (int i = 0; i < PROBE_NET_SLOTS; i++) s_probeNetIdx[i] = -1;

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

        // Paint the visual path for every bridge pair in this net.
        // paintBridgeLeds() handles M1→M1, M2→M2, M1↔M2 cross-section, and
        // non-breadboard nodes, each with the appropriate LED path geometry.
        for (int i = 0; i < resolvedCount - 1; i++)
          paintBridgeLeds(resolvedNodes[i], resolvedNodes[i + 1], col);

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

    // ── probe_connect ────────────────────────────────────────────────────────
    // Additive variant of `connect` for routing oscilloscope / function-gen
    // probe pins to breadboard nodes WITHOUT clearing existing user nets.
    //
    // Probe nets are tracked in s_probeNetIdx[] so each call replaces the
    // previously-routed probes (no duplicate accumulation) while leaving any
    // nets created by `connect` / main.py untouched.
    //
    // Request:
    //   {"cmd":"probe_connect","nets":[
    //      {"nodes":["OSC_PROBE","TOP_5"],   "color":"#00FFFF"},
    //      {"nodes":["EXT_GND","GND"],       "color":"#888888"},
    //      {"nodes":["SQUARE_WAVE_FUN","TOP_8"], "color":"#FF8000"}
    //   ]}
    //
    // Pass an empty nets[] to free all probe slots (probe-only clear that
    // preserves the rest of the user netlist).
    //
    // Response:
    //   {"ok":true,"nets_added":3,"paths":7,"skipped":0,"err_nodes":[]}
    if (!strcmp(cmd, "probe_connect"))
    {
      if (!req["nets"].is<JsonArray>())
      {
        resp["ok"]  = false;
        resp["err"] = "missing nets[]";
        sendJson(replyTo, resp);
        return;
      }

      // 1. Free previous probe slots only — leaves all other user nets intact.
      for (int i = 0; i < PROBE_NET_SLOTS; i++) {
        clearNetSlot(s_probeNetIdx[i]);
        s_probeNetIdx[i] = -1;
      }

      JsonArray netsArr = req["nets"].as<JsonArray>();
      int  netsAdded = 0;
      int  skipped   = 0;
      int  probeIdx  = 0;

      JsonDocument errDoc;
      JsonArray    errNodes = errDoc.to<JsonArray>();

      // 2. Resolve & allocate new probe nets.
      //
      // If a new entry shares any node with an already-added probe net, merge
      // it into that net instead of creating a parallel one. Two probe entries
      // that share a breadboard node (e.g. PROBE_5V→TOP_12 and SINE→TOP_12)
      // are electrically a single net, but the path finder treats separate
      // nets as separate routes — and a single inter-chip crosspoint (e.g.
      // Chip B ↔ Chip K, only one X-pin on B side) can only carry one route,
      // so the second one ends up SKIPPED.
      for (JsonVariant nv : netsArr)
      {
        JsonObject netObj = nv.as<JsonObject>();
        if (!netObj["nodes"].is<JsonArray>()) { skipped++; continue; }

        JsonArray nameArr = netObj["nodes"].as<JsonArray>();
        int resolvedNodes[MAX_NODES];
        int resolvedCount = 0;
        for (JsonVariant nameVar : nameArr) {
          const char *name = nameVar | "";
          int nodeNum = resolveNodeName(name);
          if (nodeNum < 0) { errNodes.add(name); continue; }
          if (resolvedCount < MAX_NODES) resolvedNodes[resolvedCount++] = nodeNum;
        }
        if (resolvedCount < 2) { skipped++; continue; }

        // Look for a previously-added probe net that shares a node.
        int mergeIdx = -1;
        for (int ps = 0; ps < probeIdx && mergeIdx < 0; ps++) {
          int n = s_probeNetIdx[ps];
          if (n < 8) continue;
          for (int j = 0; j < MAX_NODES && mergeIdx < 0; j++) {
            int16_t en = net[n].nodes[j];
            if (en == 0) break;
            for (int i = 0; i < resolvedCount; i++) {
              if (en == resolvedNodes[i]) { mergeIdx = n; break; }
            }
          }
        }

        if (mergeIdx >= 0) {
          // Append any nodes the existing net doesn't already contain, and
          // chain a bridge from its previous last node so the new endpoints
          // become part of the same path-finding net.
          int existingCount = 0;
          while (existingCount < MAX_NODES && net[mergeIdx].nodes[existingCount] != 0)
            existingCount++;
          int bridgeCount = 0;
          while (bridgeCount < MAX_NODES &&
                 !(net[mergeIdx].bridges[bridgeCount][0] == 0 &&
                   net[mergeIdx].bridges[bridgeCount][1] == 0))
            bridgeCount++;

          for (int i = 0; i < resolvedCount; i++) {
            int nd = resolvedNodes[i];
            bool already = false;
            for (int j = 0; j < existingCount; j++)
              if (net[mergeIdx].nodes[j] == nd) { already = true; break; }
            if (already) continue;
            if (existingCount >= MAX_NODES - 1) break;
            int16_t prev = net[mergeIdx].nodes[existingCount - 1];
            net[mergeIdx].nodes[existingCount++] = (int16_t)nd;
            if (bridgeCount < MAX_NODES) {
              net[mergeIdx].bridges[bridgeCount][0] = prev;
              net[mergeIdx].bridges[bridgeCount][1] = (int16_t)nd;
              bridgeCount++;
            }
          }
          netsAdded++;
          continue;
        }

        if (probeIdx >= PROBE_NET_SLOTS) { skipped++; continue; }

        const char    *colorStr = netObj["color"] | "#FFFFFF";
        LedMatrix::RGB_t col    = LedMatrix::wokwiColorToRgb(colorStr);
        uint32_t rawCol = ((uint32_t)col.r << 16) | ((uint32_t)col.g << 8) | col.b;

        int netIdx = addUserNet(resolvedNodes, resolvedCount, col, rawCol);
        if (netIdx < 0) { skipped++; continue; }
        s_probeNetIdx[probeIdx++] = netIdx;
        netsAdded++;
      }

      // 3. Repaint LED frame: clear, walk every active user net (existing +
      //    just-added probe nets) and re-paint via paintBridgeLeds with the
      //    net's stored colour. This preserves the visual state of nets
      //    created by main.py / `connect`, which would otherwise lose their
      //    LEDs because we don't track per-net pixels.
      LedMatrix::frameClear();
      LedMatrix::frameResetBlink();
      for (int n = 8; n < MAX_NETS; n++) {
        if (net[n].nodes[0] == 0) continue;
        uint32_t raw = net[n].rawColor;
        LedMatrix::RGB_t col = {
            (uint8_t)((raw >> 16) & 0xFF),
            (uint8_t)((raw >>  8) & 0xFF),
            (uint8_t)( raw        & 0xFF)
        };
        for (int b = 0; b < MAX_NODES; b++) {
          int16_t n1 = net[n].bridges[b][0];
          int16_t n2 = net[n].bridges[b][1];
          if (n1 == 0 && n2 == 0) break;
          paintBridgeLeds(n1, n2, col);
        }
      }

      // 4. Hardware: full re-program through the path-finding pipeline so
      //    the new probe paths join the existing user paths cleanly.
      clearAllChips();
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

    // ── measure ──────────────────────────────────────────────────────────────
    // Route a node through the on-board INA219 current sensor and return
    // the measurement.
    //
    // Request:
    //   {
    //     "cmd"   : "measure",
    //     "node"  : "TOP_5",     // node under test → connected to ISENSE_PLUS
    //     "ref"   : "GND",       // reference node  → connected to ISENSE_MINUS
    //                            //   (defaults to "GND" if omitted)
    //     "sensor": 0            // 0 or 1, selects INA219 (default 0)
    //   }
    //
    // The command clears previous user connections, routes node→ISENSE_PLUS
    // and ref→ISENSE_MINUS via the CH446Q crosspoint matrix, waits for the
    // ADC to settle, reads the INA219, and leaves the measurement path active
    // so the endpoint LEDs remain lit.
    //
    // Response:
    //   { "ok": true,
    //     "node": "TOP_5", "ref": "GND", "sensor": 0,
    //     "shunt_mv": 0.42,   "bus_v": 4.98,
    //     "current_ma": 4.2,  "power_mw": 20.9 }
    // ── measure ──────────────────────────────────────────────────────────────
    // Non-destructive: keeps existing netlist connections and LED state.
    //
    // INA219 topology:
    //   Chip L X0 = ISENSE_MINUS = IN−  (bus voltage measured here)
    //   Chip L X1 = ISENSE_PLUS  = IN+  (shunt high-side)
    //
    // Voltage-only mode (default — no "plus" field):
    //   node → ISENSE_MINUS   bus_v  = V(node) relative to GND  ← main reading
    //   ISENSE_PLUS floats    (bus-voltage ADC is independent of IN+)
    //
    // Current mode (provide "plus" field):
    //   plus → ISENSE_PLUS, node → ISENSE_MINUS
    //   Current flows:  plus → shunt → node
    //   bus_v  = V(node), current_ma = shunt_mv / shunt_resistance
    //
    // Both modes are non-destructive: existing user nets are preserved.
    // First call saves a full-brightness LED snapshot; subsequent calls in a
    // continuous loop restore from it before re-dimming.
    //
    //   {"cmd":"measure","node":"TOP_17"}
    //   {"cmd":"measure","node":"TOP_17","plus":"5V","sensor":0}
    //
    // Response:
    //   {"ok":true,"node":"TOP_17","mode":"voltage","bus_v":3.30,
    //    "shunt_mv":0.00,"current_ma":0.00,"power_mw":0.00}
    if (!strcmp(cmd, "measure"))
    {
      const char *nodeName  = req["node"]   | "";
      const char *node2Name = req["node2"]  | "";   // differential mode: node2 → ISENSE+
      const char *plusName  = req["plus"]   | "";   // current mode: supply → ISENSE+
      uint8_t     sensorIdx = (uint8_t)(req["sensor"] | 0);

      int nodeNum = resolveNodeName(nodeName);
      if (nodeNum < 0) {
        resp["ok"]   = false;  resp["err"]  = "unknown node";
        resp["node"] = nodeName;
        sendJson(replyTo, resp); return;
      }

      // Differential mode: node2 present → measure V(node2)−V(node) via shunt register
      // Current mode: plus present → measure current through node
      bool diffMode    = (node2Name[0] != '\0');
      bool currentMode = (!diffMode && plusName[0] != '\0');

      int plusNum = -1;
      if (diffMode) {
        plusNum = resolveNodeName(node2Name);
        if (plusNum < 0) {
          resp["ok"]   = false;  resp["err"] = "unknown node2";
          resp["node2"] = node2Name;
          sendJson(replyTo, resp); return;
        }
      } else if (currentMode) {
        plusNum = resolveNodeName(plusName);
        if (plusNum < 0) {
          resp["ok"]  = false;  resp["err"] = "unknown plus node";
          resp["plus"] = plusName;
          sendJson(replyTo, resp); return;
        }
      }

      if (sensorIdx > 1) {
        resp["ok"]  = false;  resp["err"] = "sensor must be 0 or 1";
        sendJson(replyTo, resp); return;
      }

      // ── Snapshot management ───────────────────────────────────────────────
      if (!LedMatrix::frameHasSnapshot()) {
        LedMatrix::frameSaveSnapshot();         // first call: save full brightness
      } else {
        LedMatrix::frameRestoreSnapshot();      // continuous: restore then re-dim
        clearNetSlot(s_measNetIdx[0]);
        clearNetSlot(s_measNetIdx[1]);
        clearNetSlot(s_measNetIdx[2]);
        s_measNetIdx[0] = s_measNetIdx[1] = s_measNetIdx[2] = -1;
      }

      // Hardware-reset chips; net[] (existing user netlist) is preserved.
      clearAllChips();

      // ── Route measurement connections ─────────────────────────────────────
      // Voltage mode: node → ISENSE_MINUS   (BBtoSF path, always works)
      // Current mode: plus → ISENSE_PLUS, node → ISENSE_MINUS
      int measNodes[2];
      LedMatrix::RGB_t colNode = { 0x00, 0xFF, 0xFF };   // cyan  — measured node
      LedMatrix::RGB_t colPlus = { 0xFF, 0xA0, 0x00 };   // amber — supply side

      // node → ISENSE_MINUS (bus_v = V(node))
      measNodes[0] = nodeNum;  measNodes[1] = ISENSE_MINUS;
      s_measNetIdx[0] = addUserNet(measNodes, 2, colNode, 0x00FFFF);

      // node2/plus → ISENSE_PLUS (diff mode and current mode)
      s_measNetIdx[1] = -1;
      if (currentMode || diffMode) {
        measNodes[0] = plusNum;  measNodes[1] = ISENSE_PLUS;
        s_measNetIdx[1] = addUserNet(measNodes, 2, colPlus, 0xFFA000);
      }

      // Re-run full pipeline (existing nets + measurement nets).
      netsToChipConnectionsFull();
      sendAllPaths(1);

      // ── LEDs: dim existing frame, spotlight measurement node ──────────────
      LedMatrix::frameDimAll(64);   // ~25 % — netlist visible but receded

      int ledNode = nodeToLedIndex(nodeNum);
      if (ledNode >= 0) LedMatrix::frameMarkEndpointIdx(ledNode, colNode);

      if (currentMode || diffMode) {
        int ledPlus = nodeToLedIndex(plusNum);
        if (ledPlus >= 0) LedMatrix::frameMarkEndpointIdx(ledPlus, colPlus);
      }

      LedMatrix::frameResetBlink();
      LedMatrix::frameApplyFull();

      // Settle: INA219 12-bit conversion ~1.1 ms/channel; 10 ms is safe.
      delay(10);

      Measurements::Reading r = Measurements::read(sensorIdx);
      if (!r.valid) {
        resp["ok"]     = false;
        resp["err"]    = "INA219 not responding";
        resp["sensor"] = (int)sensorIdx;
        sendJson(replyTo, resp); return;
      }

      resp["ok"]     = true;
      resp["sensor"] = (int)sensorIdx;
      if (diffMode) {
        // Differential voltage: shunt_mv = V(node2) - V(node)
        // node_v  = V(node)  relative to GND  (bus voltage register)
        // node2_v = V(node2) = node_v + diff_mv / 1000
        resp["mode"]    = "diff";
        resp["node"]    = nodeName;
        resp["node2"]   = node2Name;
        resp["node_v"]  = r.busV;
        resp["diff_mv"] = r.shuntMv;
        resp["node2_v"] = r.busV + r.shuntMv / 1000.0f;
      } else if (currentMode) {
        resp["mode"]       = "current";
        resp["node"]       = nodeName;
        resp["plus"]       = plusName;
        resp["bus_v"]      = r.busV;
        resp["shunt_mv"]   = r.shuntMv;
        resp["current_ma"] = r.currentMa;
        resp["power_mw"]   = r.powerMw;
      } else {
        resp["mode"]       = "voltage";
        resp["node"]       = nodeName;
        resp["bus_v"]      = r.busV;
        resp["shunt_mv"]   = r.shuntMv;
        resp["current_ma"] = r.currentMa;
        resp["power_mw"]   = r.powerMw;
      }
      sendJson(replyTo, resp);
      return;
    }

    // ── measure_diff ─────────────────────────────────────────────────────────
    // Two-pass absolute differential voltage measurement.
    // Routes each node to ISENSE_MINUS in turn and reads bus_v (0–32V, 4mV LSB).
    // diff_v = V(node2) − V(node).  No ±320mV shunt-register limit.
    //
    //   {"cmd":"measure_diff","node":"TOP_17","node2":"TOP_14"}
    //   {"cmd":"measure_diff","node":"TOP_17","node2":"TOP_14","sensor":0}
    //
    // Response:
    //   {"ok":true,"mode":"diff","method":"twopass",
    //    "node":"TOP_17","node2":"TOP_14","sensor":0,
    //    "node_v":1.35,"node2_v":5.02,"diff_v":3.67,"diff_mv":3670.0}
    if (!strcmp(cmd, "measure_diff"))
    {
      const char *nodeName  = req["node"]  | "";
      const char *node2Name = req["node2"] | "";
      uint8_t     sensorIdx = (uint8_t)(req["sensor"] | 0);

      int nodeNum  = resolveNodeName(nodeName);
      int node2Num = resolveNodeName(node2Name);

      if (nodeNum < 0) {
        resp["ok"] = false;  resp["err"] = "unknown node";  resp["node"] = nodeName;
        sendJson(replyTo, resp); return;
      }
      if (node2Num < 0) {
        resp["ok"] = false;  resp["err"] = "unknown node2";  resp["node2"] = node2Name;
        sendJson(replyTo, resp); return;
      }
      if (node2Name[0] == '\0') {
        resp["ok"] = false;  resp["err"] = "node2 required";
        sendJson(replyTo, resp); return;
      }
      if (sensorIdx > 1) {
        resp["ok"] = false;  resp["err"] = "sensor must be 0 or 1";
        sendJson(replyTo, resp); return;
      }

      // Snapshot management (same as measure)
      if (!LedMatrix::frameHasSnapshot()) {
        LedMatrix::frameSaveSnapshot();
      } else {
        LedMatrix::frameRestoreSnapshot();
        clearNetSlot(s_measNetIdx[0]);
        clearNetSlot(s_measNetIdx[1]);
        clearNetSlot(s_measNetIdx[2]);
        s_measNetIdx[0] = s_measNetIdx[1] = s_measNetIdx[2] = -1;
      }

      LedMatrix::RGB_t colNode  = { 0x00, 0xFF, 0xFF };   // cyan  — node (reference)
      LedMatrix::RGB_t colNode2 = { 0xFF, 0xA0, 0x00 };   // amber — node2

      // ── Pass 1: measure V(node) ──────────────────────────────────────────
      clearAllChips();
      int measNodes[2] = { nodeNum, ISENSE_MINUS };
      int tmpNet0 = addUserNet(measNodes, 2, colNode, 0x00FFFF);
      netsToChipConnectionsFull();
      sendAllPaths(1);
      delay(10);
      Measurements::Reading r1 = Measurements::read(sensorIdx);
      clearNetSlot(tmpNet0);

      // ── Pass 2: measure V(node2) ─────────────────────────────────────────
      clearAllChips();
      measNodes[0] = node2Num;
      int tmpNet1 = addUserNet(measNodes, 2, colNode2, 0xFFA000);
      netsToChipConnectionsFull();
      sendAllPaths(1);
      delay(10);
      Measurements::Reading r2 = Measurements::read(sensorIdx);
      clearNetSlot(tmpNet1);

      // ── Restore user nets, light both endpoint LEDs ──────────────────────
      clearAllChips();
      netsToChipConnectionsFull();
      sendAllPaths(1);

      s_measNetIdx[0] = s_measNetIdx[1] = -1;   // no active measurement nets

      LedMatrix::frameDimAll(64);
      int ledNode  = nodeToLedIndex(nodeNum);
      int ledNode2 = nodeToLedIndex(node2Num);
      if (ledNode  >= 0) LedMatrix::frameMarkEndpointIdx(ledNode,  colNode);
      if (ledNode2 >= 0) LedMatrix::frameMarkEndpointIdx(ledNode2, colNode2);
      LedMatrix::frameResetBlink();
      LedMatrix::frameApplyFull();

      if (!r1.valid || !r2.valid) {
        resp["ok"] = false;  resp["err"] = "INA219 not responding";
        resp["sensor"] = (int)sensorIdx;
        sendJson(replyTo, resp); return;
      }

      float diff_v = r2.busV - r1.busV;
      resp["ok"]      = true;
      resp["mode"]    = "diff";
      resp["method"]  = "twopass";
      resp["node"]    = nodeName;
      resp["node2"]   = node2Name;
      resp["sensor"]  = (int)sensorIdx;
      resp["node_v"]  = r1.busV;
      resp["node2_v"] = r2.busV;
      resp["diff_v"]  = diff_v;
      resp["diff_mv"] = diff_v * 1000.0f;
      sendJson(replyTo, resp);
      return;
    }

    // ── measure_clear ─────────────────────────────────────────────────────────
    // Remove measurement connections, restore the LED frame to full brightness,
    // and discard the snapshot. Sent by Python on quit or when the user
    // requests "clear".
    //
    //   {"cmd":"measure_clear"}
    //
    // Response: {"ok":true}
    if (!strcmp(cmd, "measure_clear"))
    {
      // Free the measurement net slots (up to 3: node, plus, ref→GND)
      clearNetSlot(s_measNetIdx[0]);
      clearNetSlot(s_measNetIdx[1]);
      clearNetSlot(s_measNetIdx[2]);
      s_measNetIdx[0] = s_measNetIdx[1] = s_measNetIdx[2] = -1;

      // Re-apply hardware connections for remaining (user) nets only
      clearAllChips();
      netsToChipConnectionsFull();
      sendAllPaths(1);

      // Restore full-brightness LED frame from snapshot and discard it,
      // so the next measure call saves a fresh snapshot.
      if (LedMatrix::frameHasSnapshot()) {
        LedMatrix::frameRestoreSnapshot();
        LedMatrix::frameClearSnapshot();
        LedMatrix::frameResetBlink();
        LedMatrix::frameApplyFull();
      }

      resp["ok"] = true;
      sendJson(replyTo, resp);
      return;
    }

    // ── current_viz ───────────────────────────────────────────────────────────
    // Toggle animated current-flow sparks on the LED matrix.
    //
    // The animation overlays moving "comet" sparks on top of the active netlist
    // LEDs, flowing along each net's bridge connections.  Only breadboard nodes
    // (TOP_1–30, BOTTOM_1–30) are animated; GND/5V/NANO endpoints are skipped.
    //
    //   {"cmd":"current_viz","enable":true}              // on, speed=1.0
    //   {"cmd":"current_viz","enable":true,"speed":2.0}  // on, double speed
    //   {"cmd":"current_viz","enable":false}             // off, restore frame
    //
    // Response: {"ok":true,"enabled":true,"speed":1.0}
    if (!strcmp(cmd, "current_viz"))
    {
      bool  on    = req["enable"] | false;
      float speed = req["speed"]  | 1.0f;

      // Optional bridge-pair filter.
      // "bridges": [[n1, n2], [n1, n2], ...]  — node numbers from netlist_query.
      // Absent or empty array → clear filter (animate all active bridges).
      if (req["bridges"].is<JsonArray>()) {
        JsonArray arr = req["bridges"].as<JsonArray>();
        int pairs[64];   // max 32 pairs × 2
        int pairCount = 0;
        for (JsonVariant v : arr) {
          if (v.is<JsonArray>() && pairCount < 32) {
            pairs[pairCount * 2]     = v[0] | 0;
            pairs[pairCount * 2 + 1] = v[1] | 0;
            pairCount++;
          }
        }
        CurrentViz::setFilter(pairs, pairCount);
        resp["filter_pairs"] = pairCount;
      } else {
        CurrentViz::clearFilter();
      }

      CurrentViz::enable(on, speed);
      resp["ok"]      = true;
      resp["enabled"] = on;
      resp["speed"]   = speed;
      sendJson(replyTo, resp);
      return;
    }

    // ── measure_sweep ────────────────────────────────────────────────────────
    // Route a component between `node` (ISENSE_MINUS side) and `ref` (GND side)
    // through the INA219 and take N V+I samples at fixed intervals.
    // Used for resistor V-I characterisation and capacitor RC-curve fitting.
    //
    // Request:
    //   {"cmd":"measure_sweep",
    //    "node":"TOP_5",          // component terminal → ISENSE_MINUS
    //    "plus":"5V",             // supply → ISENSE_PLUS
    //    "ref":"TOP_10",          // other component terminal → GND  (default "GND")
    //    "samples":40,            // 1-80 (default 20)
    //    "interval_ms":5,         // ≥1 ms between samples (default 10)
    //    "discharge_ms":200,      // >0: discharge `node` through `ref` first (capacitors)
    //    "sensor":0}
    //
    // Response:
    //   {"ok":true,"node":"TOP_5","plus":"5V","ref":"TOP_10","count":40,
    //    "samples":[{"t_ms":0,"v":4.98,"i":9.95}, ...]}
    if (!strcmp(cmd, "measure_sweep"))
    {
      const char *nodeName    = req["node"]         | "";
      const char *plusName    = req["plus"]         | "";
      const char *refName     = req["ref"]          | "GND";
      int         nSamples    = req["samples"]      | 20;
      int         intervalMs  = req["interval_ms"]  | 10;
      int         dischargeMs = req["discharge_ms"] | 0;
      uint8_t     sensorIdx   = (uint8_t)(req["sensor"] | 0);

      if (nSamples  <  1) nSamples  = 1;
      if (nSamples  > 80) nSamples  = 80;
      if (intervalMs < 1) intervalMs = 1;

      int nodeNum = resolveNodeName(nodeName);
      int plusNum = resolveNodeName(plusName);
      int refNum  = resolveNodeName(refName);

      if (nodeNum < 0) {
        resp["ok"] = false; resp["err"] = "unknown node"; resp["node"] = nodeName;
        sendJson(replyTo, resp); return;
      }
      if (plusNum < 0) {
        resp["ok"] = false; resp["err"] = "unknown plus"; resp["plus"] = plusName;
        sendJson(replyTo, resp); return;
      }
      if (refNum < 0) {
        resp["ok"] = false; resp["err"] = "unknown ref"; resp["ref"] = refName;
        sendJson(replyTo, resp); return;
      }
      if (sensorIdx > 1) {
        resp["ok"] = false; resp["err"] = "sensor must be 0 or 1";
        sendJson(replyTo, resp); return;
      }

      // Snapshot management
      if (!LedMatrix::frameHasSnapshot()) {
        LedMatrix::frameSaveSnapshot();
      } else {
        LedMatrix::frameRestoreSnapshot();
        clearNetSlot(s_measNetIdx[0]);
        clearNetSlot(s_measNetIdx[1]);
        clearNetSlot(s_measNetIdx[2]);
        s_measNetIdx[0] = s_measNetIdx[1] = s_measNetIdx[2] = -1;
      }

      LedMatrix::RGB_t colNode = { 0x00, 0xFF, 0xFF };   // cyan  — measured node
      LedMatrix::RGB_t colPlus = { 0xFF, 0xA0, 0x00 };   // amber — supply
      LedMatrix::RGB_t colRef  = { 0x80, 0x80, 0x80 };   // grey  — reference/GND side

      // ── Route ref → GND if ref is not already GND ────────────────────────
      s_measNetIdx[2] = -1;
      if (refNum != GND) {
        int refNodes[2] = { refNum, GND };
        s_measNetIdx[2] = addUserNet(refNodes, 2, colRef, 0x808080);
      }

      // ── Optional discharge phase ──────────────────────────────────────────
      // Connect node directly to GND for dischargeMs (drains capacitor to 0V).
      if (dischargeMs > 0) {
        clearAllChips();
        int disNodes[2] = { nodeNum, GND };
        int disNetIdx = addUserNet(disNodes, 2, colNode, 0x00FFFF);
        netsToChipConnectionsFull();
        sendAllPaths(1);
        delay((uint32_t)dischargeMs);
        clearNetSlot(disNetIdx);
      }

      // ── Set up measurement circuit ────────────────────────────────────────
      clearAllChips();
      int measNodes[2];
      measNodes[0] = nodeNum;  measNodes[1] = ISENSE_MINUS;
      s_measNetIdx[0] = addUserNet(measNodes, 2, colNode, 0x00FFFF);
      measNodes[0] = plusNum;  measNodes[1] = ISENSE_PLUS;
      s_measNetIdx[1] = addUserNet(measNodes, 2, colPlus, 0xFFA000);
      netsToChipConnectionsFull();
      sendAllPaths(1);

      // ── LEDs: dim frame, mark component endpoints ─────────────────────────
      LedMatrix::frameDimAll(64);
      int ledNode = nodeToLedIndex(nodeNum);
      int ledPlus = nodeToLedIndex(plusNum);
      int ledRef  = nodeToLedIndex(refNum);
      if (ledNode >= 0) LedMatrix::frameMarkEndpointIdx(ledNode, colNode);
      if (ledPlus >= 0) LedMatrix::frameMarkEndpointIdx(ledPlus, colPlus);
      if (ledRef  >= 0) LedMatrix::frameMarkEndpointIdx(ledRef,  colRef);
      LedMatrix::frameResetBlink();
      LedMatrix::frameApplyFull();

      // Settle before first sample
      delay(5);

      // ── Sampling loop ─────────────────────────────────────────────────────
      uint32_t t0 = millis();
      JsonArray sampArr = resp["samples"].to<JsonArray>();

      for (int s = 0; s < nSamples; s++) {
        Measurements::Reading r = Measurements::read(sensorIdx);
        JsonObject samp = sampArr.add<JsonObject>();
        samp["t_ms"] = (int)(millis() - t0);
        samp["v"]    = r.valid ? r.busV      : 0.0f;
        samp["i"]    = r.valid ? r.currentMa : 0.0f;
        if (s < nSamples - 1) delay((uint32_t)intervalMs);
      }

      resp["ok"]    = true;
      resp["node"]  = nodeName;
      resp["plus"]  = plusName;
      resp["ref"]   = refName;
      resp["count"] = nSamples;
      sendJson(replyTo, resp);
      return;
    }

    // ── led_dump ──────────────────────────────────────────────────────────────
    // Dump the current LED framebuffer state for debugging.
    // Outputs raw text lines followed by a JSON ACK:
    //   LED_DUMP_BEGIN
    //   PATH:<2400 hex chars>   (path RGB for all 400 LEDs)
    //   ENDP:<2400 hex chars>   (endpoint RGB for all 400 LEDs)
    //   EP:<400 chars>          ('1'=endpoint, '0'=path)
    //   LED_DUMP_END
    //   {"ok":true,"cmd":"led_dump"}
    if (!strcmp(cmd, "led_dump"))
    {
      LedMatrix::frameDump(replyTo);
      resp["ok"]  = true;
      resp["cmd"] = "led_dump";
      sendJson(replyTo, resp);
      return;
    }

    // ── animation ─────────────────────────────────────────────────────────────
    // Enable or disable the connect/disconnect LED animations at runtime.
    // Useful during testing to skip the ~700 ms connectionSuccess and ~600 ms
    // connectionLost animations that play on every USB plug/unplug.
    //
    //   {"cmd":"animation","enable":false}   — disable animations
    //   {"cmd":"animation","enable":true}    — re-enable animations (default)
    //
    // The flag resets to true on power-cycle.
    //
    // Response: {"ok":true,"animation":false}
    if (!strcmp(cmd, "animation"))
    {
      bool en = req["enable"] | true;
      JumperZ_SEQUENCE::setAnimEnabled(en);
      resp["ok"]        = true;
      resp["animation"] = en;
      sendJson(replyTo, resp);
      return;
    }

    // ── settings ──────────────────────────────────────────────────────────────
    // Read or update persistent board settings stored in the external EEPROM.
    //
    //   {"cmd":"settings"}                          → get all settings
    //   {"cmd":"settings","action":"get"}            → same
    //   {"cmd":"settings","action":"set",
    //    "brightness":80,"conn_anim":true}           → update field(s), persist
    //   {"cmd":"settings","action":"verify"}         → read-back EEPROM vs RAM
    //   {"cmd":"settings","action":"reset"}          → restore factory defaults
    //
    // Every response includes "eeprom_ok" so you can immediately see whether
    // the EEPROM is reachable.  "set" also includes "save_ok".
    //
    // Response (get/set): {"ok":true,"brightness":50,"conn_anim":false,
    //                      "disconn_anim":false,"eeprom_ok":true}
    // Response (verify):  {"ok":true,"match":true,"eeprom_ok":true}
    if (!strcmp(cmd, "settings"))
    {
      const char *action = req["action"] | "get";

      if (!strcmp(action, "verify"))
      {
        bool match = Settings::verify();
        resp["ok"]        = true;
        resp["match"]     = match;
        resp["eeprom_ok"] = Settings::eepromOk();
        sendJson(replyTo, resp);
        return;
      }

      if (!strcmp(action, "reset"))
      {
        bool ok = Settings::reset();
        LedMatrix::setBrightness(Settings::get().brightness);
        JumperZ_SEQUENCE::setAnimEnabled(Settings::get().conn_anim);
        resp["save_ok"] = ok;
      }
      else if (!strcmp(action, "set"))
      {
        Settings::Config &cfg = Settings::get();

        if (!req["brightness"].isNull())
        {
          uint8_t b = (uint8_t)constrain((int)req["brightness"], 0, 255);
          cfg.brightness = b;
          LedMatrix::setBrightness(b);   // apply immediately
        }
        if (!req["conn_anim"].isNull())
        {
          cfg.conn_anim = (bool)req["conn_anim"];
          JumperZ_SEQUENCE::setAnimEnabled(cfg.conn_anim);
        }
        if (!req["disconn_anim"].isNull())
          cfg.disconn_anim = (bool)req["disconn_anim"];
        if (!req["osc_conn_style"].isNull())
          cfg.osc_conn_style    = (uint8_t)constrain((int)req["osc_conn_style"], 0, 4);
        if (!req["osc_disconn_style"].isNull())
          cfg.osc_disconn_style = (uint8_t)constrain((int)req["osc_disconn_style"], 0, 3);

        bool ok = Settings::save();
        resp["save_ok"] = ok;
      }
      // "get" (default) falls through to the response below.

      const Settings::Config &cfg = Settings::get();
      resp["ok"]                = true;
      resp["brightness"]        = cfg.brightness;
      resp["conn_anim"]         = cfg.conn_anim;
      resp["disconn_anim"]      = cfg.disconn_anim;
      resp["osc_conn_style"]    = cfg.osc_conn_style;
      resp["osc_disconn_style"] = cfg.osc_disconn_style;
      resp["eeprom_ok"]         = Settings::eepromOk();
      sendJson(replyTo, resp);
      return;
    }

    // ── stm_cmd ───────────────────────────────────────────────────────────────
    // Forward a command string to the STM32 via the ESP32-S3 byte pipe.
    // The bridge (RP2040 <-> ESP32 <-> STM32) is transparent, so whatever we
    // write here lands byte-for-byte on the STM32 USART.  STM32 replies flow
    // back out of USBSer2 (the OSC_FUN_PORT on the host) — they are NOT
    // surfaced here on USBSer1.
    //
    //   {"cmd":"stm_cmd","data":"#A#"}
    //
    // Response: {"ok":true,"sent":"#A#"}
    if (!strcmp(cmd, "stm_cmd"))
    {
      const char* data = req["data"] | "";
      if (data[0] == '\0') {
        resp["ok"]  = false;
        resp["err"] = "missing data field";
        sendJson(replyTo, resp);
        return;
      }
      UARTMainBridge::sendLine(data);   // raw data + '\n', no prefix
      resp["ok"]   = true;
      resp["sent"] = data;
      sendJson(replyTo, resp);
      return;
    }

    resp["ok"] = false;
    resp["err"] = "unknown cmd";
    resp["cmd"] = cmd;
    sendJson(replyTo, resp);
  }
}