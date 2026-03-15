"""
jz_map.py — convert Wokwi breadboard node strings to JumperZ node name strings.

Wokwi node formats:
  bb1:<col>t.<a-e>   top-half terminal strip (M1), col 1..30
  bb1:<col>b.<f-j>   bottom-half terminal strip (M2), col 1..30
  bb1:tp.<1-25>      top positive power rail
  bb1:tn.<1-25>      top negative power rail
  bb1:bp.<1-25>      bottom positive power rail
  bb1:bn.<1-25>      bottom negative power rail
  nano:<pin>         Arduino Nano header pin

JumperZ node names (resolved via sfMappings[] on the firmware):
  "TOP_1" .. "TOP_30"       breadboard top rows, node numbers 1..30
  "BOTTOM_1" .. "BOTTOM_30" breadboard bottom rows, node numbers 31..60
  "5V"                      positive power rail
  "GND"                     negative power rail
  "NANO_D0" .. "NANO_D13"   Nano digital pins
  "NANO_A0" .. "NANO_A7"    Nano analog pins
  "NANO_RESET"              Nano reset pin
  "NANO_AREF"               Nano AREF pin

Any other Wokwi node (component pins, etc.) returns None.
"""

import re

_ROW_AE = "abcde"
_ROW_FJ = "fghij"

_RAIL_RE = re.compile(r"^bb1:(tp|tn|bp|bn)\.(\d+)$")
_HOLE_RE = re.compile(r"^bb1:(\d+)([tb])\.([a-j])$")
_NANO_RE = re.compile(r"^nano:(.+)$")

# Wokwi Arduino Nano pin name → JumperZ node name
_NANO_PIN_MAP = {
    "0":    "NANO_D0",   "RX":   "NANO_D0",
    "1":    "NANO_D1",   "TX":   "NANO_D1",
    "2":    "NANO_D2",
    "3":    "NANO_D3",
    "4":    "NANO_D4",
    "5":    "NANO_D5",
    "6":    "NANO_D6",
    "7":    "NANO_D7",
    "8":    "NANO_D8",
    "9":    "NANO_D9",
    "10":   "NANO_D10",
    "11":   "NANO_D11",
    "12":   "NANO_D12",
    "13":   "NANO_D13",
    "A0":   "NANO_A0",
    "A1":   "NANO_A1",
    "A2":   "NANO_A2",
    "A3":   "NANO_A3",
    "A4":   "NANO_A4",
    "A5":   "NANO_A5",
    "A6":   "NANO_A6",
    "A7":   "NANO_A7",
    "RST":  "NANO_RESET",
    "RST2": "NANO_RESET",
    "AREF": "NANO_AREF",
    "GND":  "GND",
    "GND.1":"GND",
    "GND.2":"GND",
    "5V":   "5V",
    "VIN":  "5V",
    "3V3":  "3.3V",
}


def wokwi_node_to_jz_name(node: str):
    """
    Returns the JumperZ node name string for a Wokwi node, or None.

    Examples:
      "bb1:5t.a"  -> "TOP_5"
      "bb1:5t.c"  -> "TOP_5"   (same column = same node)
      "bb1:5b.f"  -> "BOTTOM_5"
      "bb1:tp.3"  -> "5V"
      "bb1:tn.3"  -> "GND"
      "nano:6"    -> "NANO_D6"
      "nano:GND.2"-> "GND"
      "nano:A3"   -> "NANO_A3"
      "r1:1"      -> None       (component pin, not a mappable node)
    """
    node = node.strip()

    m = _RAIL_RE.match(node)
    if m:
        rail = m.group(1)
        return "5V" if rail in ("tp", "bp") else "GND"

    m = _HOLE_RE.match(node)
    if m:
        col = int(m.group(1))   # 1..30
        side = m.group(2)       # "t" or "b"
        row_ch = m.group(3)     # a..j

        if side == "t" and row_ch in _ROW_AE:
            return f"TOP_{col}"
        if side == "b" and row_ch in _ROW_FJ:
            return f"BOTTOM_{col}"

    m = _NANO_RE.match(node)
    if m:
        return _NANO_PIN_MAP.get(m.group(1))

    return None
