"""
led_diagnostic.py — LED matrix layout diagnostic tool.

Sends specific test patterns to determine the physical LED layout.
Run each test and note WHERE on the physical board the LEDs appear.

Usage:
    python led_diagnostic.py

Follow the prompts. After each pattern, press Enter to advance.
"""

import json, time, serial, serial.tools.list_ports

VID_TOKEN = "1D51"
PID_TOKEN = "ACAB"
BRIDGE_LOC_SUFFIX = "X.2"


def _find_bridge_port():
    for p in serial.tools.list_ports.comports():
        hwid = (getattr(p, "hwid", "") or "").upper()
        if VID_TOKEN not in hwid or PID_TOKEN not in hwid:
            continue
        key = "LOCATION="
        i = hwid.find(key)
        if i >= 0:
            loc = hwid[i + len(key):].strip()
            suf = loc.split(":")[-1].strip() if ":" in loc else loc
            if suf == BRIDGE_LOC_SUFFIX:
                return p.device
    return None


def _send(port, payload):
    line = json.dumps(payload, separators=(",", ":")) + "\n"
    with serial.Serial(port, baudrate=115200, timeout=1, write_timeout=1) as s:
        time.sleep(0.15)
        s.write(line.encode("utf-8"))
        s.flush()


def _test_point(port, section, row, col, color, label):
    """Light a single blinking dot at the given logical coordinate."""
    _send(port, {"cmd": "wokwi_wires", "wires": [
        {"a": [section, row, col], "b": [section, row, col], "color": color}
    ]})
    input(f"  {label:40s}  → press Enter to continue...")


def _test_line(port, points, color, label):
    """Light a sequence of points as a path."""
    _send(port, {"cmd": "wokwi_wires", "wires": [
        {"points": points, "color": color}
    ]})
    input(f"  {label:40s}  → press Enter to continue...")


def _clear(port):
    _send(port, {"cmd": "clear"})


def main():
    port = _find_bridge_port()
    if not port:
        print("ERROR: could not find bridge port (JZ NETSH). Is the board plugged in?")
        return
    print(f"Found bridge port: {port}")
    print()

    # ── TEST 1: M1 corner dots ─────────────────────────────────────────────
    print("=== TEST 1: M1 section corner dots (one at a time) ===")
    print("M1 is the TOP half of the breadboard (rows a-e, cols 1-30)")
    print()

    _clear(port)
    _test_point(port, "M1", 0, 0,  "red",   "M1 TOP-LEFT   (row a, col 1)")
    _clear(port)
    _test_point(port, "M1", 0, 29, "green", "M1 TOP-RIGHT  (row a, col 30)")
    _clear(port)
    _test_point(port, "M1", 4, 0,  "blue",  "M1 BOTTOM-LEFT  (row e, col 1)")
    _clear(port)
    _test_point(port, "M1", 4, 29, "white", "M1 BOTTOM-RIGHT (row e, col 30)")

    print()
    print("=== TEST 2: M2 section corner dots ===")
    print("M2 is the BOTTOM half of the breadboard (rows f-j, cols 1-30)")
    print()

    _clear(port)
    _test_point(port, "M2", 0, 0,  "red",   "M2 TOP-LEFT   (row f, col 1)")
    _clear(port)
    _test_point(port, "M2", 0, 29, "green", "M2 TOP-RIGHT  (row f, col 30)")
    _clear(port)
    _test_point(port, "M2", 4, 0,  "blue",  "M2 BOTTOM-LEFT  (row j, col 1)")
    _clear(port)
    _test_point(port, "M2", 4, 29, "white", "M2 BOTTOM-RIGHT (row j, col 30)")

    print()
    print("=== TEST 3: Rail corners ===")
    print()

    _clear(port)
    _test_point(port, "T", 0, 0,  "red",   "TOP RAIL: positive, col 1 (leftmost)")
    _clear(port)
    _test_point(port, "T", 0, 24, "green", "TOP RAIL: positive, col 25 (rightmost)")
    _clear(port)
    _test_point(port, "T", 1, 0,  "blue",  "TOP RAIL: negative, col 1 (leftmost)")
    _clear(port)
    _test_point(port, "T", 1, 24, "white", "TOP RAIL: negative, col 25 (rightmost)")

    print()
    print("=== TEST 4: Full section sweeps — shows DIRECTION ===")
    print("A line will sweep across. Watch the direction.")
    print()

    _clear(port)
    # Horizontal sweep: M1 row a, all cols left→right
    pts = [["M1", 0, c] for c in range(30)]
    _test_line(port, pts, "cyan", "M1 row 'a' full sweep (col 1→30)")

    _clear(port)
    # Vertical sweep: M1 col 0, all rows top→bottom
    pts = [["M1", r, 0] for r in range(5)]
    _test_line(port, pts, "yellow", "M1 col 1 full height (row a→e)")

    _clear(port)
    # M2 horizontal sweep
    pts = [["M2", 0, c] for c in range(30)]
    _test_line(port, pts, "cyan", "M2 row 'f' full sweep (col 1→30)")

    _clear(port)
    # Top rail full sweep row 0
    pts = [["T", 0, c] for c in range(25)]
    _test_line(port, pts, "orange", "TOP positive rail full sweep (col 1→25)")

    print()
    print("=== TEST 5: Wire 4 and Wire 5 reference positions ===")
    print("These match the actual Wokwi circuit wires.")
    print()

    _clear(port)
    # Wire 5 from the Wokwi circuit: M1 col 17, rows a-e (vertical blue)
    pts = [["M1", r, 16] for r in range(5)]
    _test_line(port, pts, "blue", "Wire5: M1 col 17 vertical (should be right of center)")

    _clear(port)
    # Wire 4 from the Wokwi circuit: M2 row h, cols 4-12 (horizontal blue)
    pts = [["M2", 2, c] for c in range(3, 12)]
    _test_line(port, pts, "blue", "Wire4: M2 row h, cols 4-12 (should be left area)")

    _clear(port)
    print("Done. Report back where each pattern appeared physically!")
    print()
    print("Key questions:")
    print("  1. For M1 TOP-LEFT (red dot): was it at top-LEFT or top-RIGHT of M1?")
    print("  2. For M1 TOP-RIGHT (green dot): was it at top-LEFT or top-RIGHT of M1?")
    print("  3. For the M1 row-a sweep: did LEDs move LEFT→RIGHT or RIGHT→LEFT?")
    print("  4. For Wire5 (M1 col 17 blue vertical): was it CENTER-RIGHT or far LEFT?")


if __name__ == "__main__":
    main()
