#include "json_bridge.h"


namespace JsonBridge
{
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
    LedMatrix::frameClear();
    LedMatrix::clear();
    LedMatrix::show();
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

    resp["ok"] = false;
    resp["err"] = "unknown cmd";
    resp["cmd"] = cmd;
    sendJson(replyTo, resp);
  }
}