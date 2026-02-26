

#include "json_bridge.h"
#include "configuration.h"   // for LedMatrix::NUM_LEDS + mapping funcs

namespace JsonBridge
{
  // ---------------- internal types ----------------
  struct RGB
  {
    uint8_t r, g, b;
  };

  // ---------------- strip pointer ----------------
  static Adafruit_NeoPixel *g_strip = nullptr;

  // ---------------- framebuffer + blink state ----------------
  static uint8_t pathR[LedMatrix::NUM_LEDS];
  static uint8_t pathG[LedMatrix::NUM_LEDS];
  static uint8_t pathB[LedMatrix::NUM_LEDS];

  static uint8_t endR[LedMatrix::NUM_LEDS];
  static uint8_t endG[LedMatrix::NUM_LEDS];
  static uint8_t endB[LedMatrix::NUM_LEDS];

  static bool isEndpoint[LedMatrix::NUM_LEDS];
  static bool haveFrame = false;

  static bool blinkOn = true;
  static uint32_t lastBlinkMs = 0;
  static const uint32_t BLINK_PERIOD_MS = 350;

  // ---------------- helpers ----------------
  static void sendJson(Stream &s, JsonDocument &doc)
  {
    serializeJson(doc, s);
    s.print('\n');
  }

  static int logicalToIndex(const char *sec, int row, int col)
  {
    if (!sec) return -1;

    uint16_t idx = 0xFFFF;

    if (!strcmp(sec, "T"))      idx = LedMatrix::topRailIndex((uint8_t)row, (uint8_t)col);
    else if (!strcmp(sec, "B")) idx = LedMatrix::bottomRailIndex((uint8_t)row, (uint8_t)col);
    else if (!strcmp(sec, "M1")) idx = LedMatrix::mid1Index((uint8_t)row, (uint8_t)col);
    else if (!strcmp(sec, "M2")) idx = LedMatrix::mid2Index((uint8_t)row, (uint8_t)col);

    return (idx == 0xFFFF) ? -1 : (int)idx;
  }

  static int hexNibble(char c)
  {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return 10 + (c - 'a');
    if (c >= 'A' && c <= 'F') return 10 + (c - 'A');
    return -1;
  }

  static bool parseHexColor(const char *s, RGB &out)
  {
    // "#RRGGBB"
    if (!s || s[0] != '#' || !s[1] || !s[2] || !s[3] || !s[4] || !s[5] || !s[6]) return false;

    int r1 = hexNibble(s[1]), r2 = hexNibble(s[2]);
    int g1 = hexNibble(s[3]), g2 = hexNibble(s[4]);
    int b1 = hexNibble(s[5]), b2 = hexNibble(s[6]);
    if (r1 < 0 || r2 < 0 || g1 < 0 || g2 < 0 || b1 < 0 || b2 < 0) return false;

    out.r = (uint8_t)((r1 << 4) | r2);
    out.g = (uint8_t)((g1 << 4) | g2);
    out.b = (uint8_t)((b1 << 4) | b2);
    return true;
  }

  static RGB wokwiColorToRgb(const char *name)
  {
    RGB c{255, 255, 255}; // default white
    if (!name || name[0] == '\0') return c;

    if (name[0] == '#')
    {
      RGB hx;
      if (parseHexColor(name, hx)) return hx;
      return c;
    }

    if (!strcmp(name, "red"))    return RGB{255, 0, 0};
    if (!strcmp(name, "green"))  return RGB{0, 255, 0};
    if (!strcmp(name, "blue"))   return RGB{0, 0, 255};
    if (!strcmp(name, "yellow")) return RGB{255, 255, 0};
    if (!strcmp(name, "orange")) return RGB{255, 128, 0};
    if (!strcmp(name, "purple")) return RGB{180, 0, 255};
    if (!strcmp(name, "pink"))   return RGB{255, 0, 150};
    if (!strcmp(name, "cyan"))   return RGB{0, 255, 255};
    if (!strcmp(name, "white"))  return RGB{255, 255, 255};
    if (!strcmp(name, "black"))  return RGB{10, 10, 10};   // visible “black”
    if (!strcmp(name, "gray"))   return RGB{80, 80, 80};
    if (!strcmp(name, "grey"))   return RGB{80, 80, 80};
    if (!strcmp(name, "brown"))  return RGB{120, 60, 0};

    return c;
  }

    void clearFrame()
  {
    for (int i = 0; i < (int)LedMatrix::NUM_LEDS; i++)
    {
      pathR[i] = pathG[i] = pathB[i] = 0;
      endR[i] = endG[i] = endB[i] = 0;
      isEndpoint[i] = false;
    }
    haveFrame = false;
  }

  static void paintPathIdx(int idx, const RGB &c)
  {
    if (idx < 0 || idx >= (int)LedMatrix::NUM_LEDS) return;
    pathR[idx] = c.r;
    pathG[idx] = c.g;
    pathB[idx] = c.b;
  }

  static void markEndpointIdx(int idx, const RGB &c)
  {
    if (idx < 0 || idx >= (int)LedMatrix::NUM_LEDS) return;
    isEndpoint[idx] = true;
    endR[idx] = c.r;
    endG[idx] = c.g;
    endB[idx] = c.b;
  }

  static void applyFullFrameToStrip()
  {
    if (!g_strip) return;

    for (int i = 0; i < (int)LedMatrix::NUM_LEDS; i++)
      g_strip->setPixelColor((uint16_t)i, g_strip->Color(pathR[i], pathG[i], pathB[i]));

    for (int i = 0; i < (int)LedMatrix::NUM_LEDS; i++)
    {
      if (!isEndpoint[i]) continue;

      if (blinkOn)
        g_strip->setPixelColor((uint16_t)i, g_strip->Color(endR[i], endG[i], endB[i]));
      else
        g_strip->setPixelColor((uint16_t)i, g_strip->Color(pathR[i], pathG[i], pathB[i]));
    }

    g_strip->show();
    haveFrame = true;
  }

  static void applyEndpointsOnly()
  {
    if (!g_strip) return;

    for (int i = 0; i < (int)LedMatrix::NUM_LEDS; i++)
    {
      if (!isEndpoint[i]) continue;

      if (blinkOn)
        g_strip->setPixelColor((uint16_t)i, g_strip->Color(endR[i], endG[i], endB[i]));
      else
        g_strip->setPixelColor((uint16_t)i, g_strip->Color(pathR[i], pathG[i], pathB[i]));
    }

    g_strip->show();
  }

  // ---------------- public API ----------------
  void begin(Adafruit_NeoPixel &strip)
  {
    g_strip = &strip;
    clearFrame();
    blinkOn = true;
    lastBlinkMs = millis();
  }

  void clear()
  {
    clearFrame();
    if (g_strip)
    {
      g_strip->clear();
      g_strip->show();
    }
  }

  void tick()
  {
    if (!haveFrame) return;

    uint32_t now = millis();
    if (now - lastBlinkMs >= BLINK_PERIOD_MS)
    {
      lastBlinkMs = now;
      blinkOn = !blinkOn;
      applyEndpointsOnly();
    }
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
      resp["blink_ms"] = (int)BLINK_PERIOD_MS;
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

      clearFrame();
      blinkOn = true;
      lastBlinkMs = millis();

      JsonArray wires = req["wires"].as<JsonArray>();
      int pathPainted = 0;
      int endpointsMarked = 0;

      for (JsonVariant wv : wires)
      {
        JsonObject wire = wv.as<JsonObject>();
        const char *cname = wire["color"] | "";
        RGB col = wokwiColorToRgb(cname);

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

            int idx = logicalToIndex(sec, row, coln);
            if (idx < 0) continue;

            if (firstIdx < 0) firstIdx = idx;
            lastIdx = idx;

            paintPathIdx(idx, col);
            pathPainted++;
          }

          if (firstIdx >= 0) { markEndpointIdx(firstIdx, col); endpointsMarked++; }
          if (lastIdx >= 0)  { markEndpointIdx(lastIdx, col); endpointsMarked++; }

          continue;
        }

        // Otherwise: only endpoints a/b exist
        JsonArray a = wire["a"].as<JsonArray>();
        JsonArray b = wire["b"].as<JsonArray>();
        if (a.size() < 3 || b.size() < 3) continue;

        int idxA = logicalToIndex(a[0] | "", a[1] | -1, a[2] | -1);
        int idxB = logicalToIndex(b[0] | "", b[1] | -1, b[2] | -1);

        if (idxA >= 0)
        {
          paintPathIdx(idxA, col); pathPainted++;
          markEndpointIdx(idxA, col); endpointsMarked++;
        }

        if (idxB >= 0)
        {
          paintPathIdx(idxB, col); pathPainted++;
          markEndpointIdx(idxB, col); endpointsMarked++;
        }
      }

      applyFullFrameToStrip();

      resp["ok"] = true;
      resp["path_leds"] = pathPainted;
      resp["endpoints"] = endpointsMarked;
      resp["blink_ms"] = (int)BLINK_PERIOD_MS;
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