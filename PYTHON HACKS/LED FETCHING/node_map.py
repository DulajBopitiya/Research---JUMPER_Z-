"""
node_map.py — JumperZ node number ↔ name mapping.

Mirrors pin_map.h exactly.  Import this wherever you need to convert between
the raw node numbers returned by netlist_query and human-readable names.

Quick reference:
  TOP_1  – TOP_30   → node numbers 1  – 30   (M1 breadboard rows)
  BOTTOM_1–BOTTOM_30 → node numbers 31 – 60   (M2 breadboard rows)
  NANO_D0–NANO_A7   → node numbers 70 – 93
  GND               → 100
  3V3               → 103
  5V                → 105
  DAC0/DAC1         → 106/107
  ISENSE+/ISENSE-   → 108/109
  ADC0–ADC3         → 110–113
  EXT_1–EXT_35      → 129–163
  EXT_Tx/EXT_Rx     → 168/169
"""

# ── number → name ─────────────────────────────────────────────────────────────

NODE_NAME: dict[int, str] = {}

for _i in range(1, 31):
    NODE_NAME[_i]      = f"TOP_{_i}"        # 1–30
for _i in range(1, 31):
    NODE_NAME[30 + _i] = f"BOTTOM_{_i}"     # 31–60

_NANO = [
    "D0","D1","D2","D3","D4","D5","D6","D7",
    "D8","D9","D10","D11","D12","D13",
    "RESET","AREF",
    "A0","A1","A2","A3","A4","A5","A6","A7",
]
for _i, _n in enumerate(_NANO):
    NODE_NAME[70 + _i] = f"NANO_{_n}"       # 70–93

NODE_NAME.update({
    100: "GND",
    103: "3V3",
    105: "5V",
    106: "DAC0",
    107: "DAC1",
    108: "ISENSE+",
    109: "ISENSE-",
    110: "ADC0",
    111: "ADC1",
    112: "ADC2",
    113: "ADC3",
    127: "EMPTY",
})

for _i in range(1, 36):
    NODE_NAME[128 + _i] = f"EXT_{_i}"       # 129–163
NODE_NAME[168] = "EXT_Tx"
NODE_NAME[169] = "EXT_Rx"


# ── name → number (reverse map) ───────────────────────────────────────────────

NODE_NUM: dict[str, int] = {name: num for num, name in NODE_NAME.items()}


# ── helpers ───────────────────────────────────────────────────────────────────

def name(node_num: int) -> str:
    """Return human-readable name for a node number, e.g. 105 → '5V'."""
    return NODE_NAME.get(node_num, f"NODE_{node_num}")


def num(node_name: str) -> int:
    """Return node number for a name, e.g. '5V' → 105.  Returns -1 if unknown."""
    return NODE_NUM.get(node_name, -1)


def is_supply(node_num: int) -> bool:
    """True for GND, 3V3, 5V, DAC0, DAC1."""
    return node_num in (100, 103, 105, 106, 107)


def is_breadboard(node_num: int) -> bool:
    """True for TOP_1–TOP_30 and BOTTOM_1–BOTTOM_30."""
    return (1 <= node_num <= 30) or (31 <= node_num <= 60)
