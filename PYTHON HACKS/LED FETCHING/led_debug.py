#!/usr/bin/env python3
"""
led_debug.py  —  JumperZ LED Matrix Debug Viewer

Fetches the current framebuffer from the board via {"cmd":"led_dump"} and
renders it as an ANSI-coloured map in the terminal.
Endpoint LEDs (blinking on the board) are marked with a ◆ character.

Usage:
    python led_debug.py                    # single snapshot
    python led_debug.py --loop             # refresh every second
    python led_debug.py --loop --interval 0.5
    python led_debug.py --port COM5        # explicit port
    python led_debug.py --raw              # print raw hex (good for sharing)

Requires:  pip install pyserial   (same as the rest of the tools here)
"""

import argparse
import json
import sys
import time

import serial
import serial.tools.list_ports

from bridge_send import find_ports

NUM_LEDS = 400


# ── LED index formulas (mirror of Led_Matrix.cpp) ─────────────────────────────

def top_rail_index(row, col):
    block     = col // 5
    local_col = col % 5
    base      = block * 10          # TOP_BASE = 0
    return base + local_col if row == 0 else base + (9 - local_col)

def bottom_rail_index(row, col):
    block     = col // 5
    local_col = col % 5
    base      = 350 + block * 10   # BOTTOM_BASE = 350
    return base + local_col if row == 0 else base + (9 - local_col)

def mid1_index(row, col):
    return 50 + col * 5 + row      # column-major

def mid2_index(row, col):
    return 200 + col * 5 + row     # column-major


# ── Serial fetch ──────────────────────────────────────────────────────────────

def fetch_dump(port, baud=115200, timeout=5.0):
    """
    Send {"cmd":"led_dump"} and collect the raw text lines.
    Returns dict: {"PATH": <hex str>, "ENDP": <hex str>, "EP": <str>}
    """
    with serial.Serial(port, baud, timeout=timeout) as ser:
        time.sleep(0.1)  # Windows CDC settle
        ser.reset_input_buffer()
        ser.write(b'{"cmd":"led_dump"}\n')

        data   = {}
        active = False
        end    = time.time() + timeout

        while time.time() < end:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("ascii", errors="replace").strip()

            if line == "LED_DUMP_BEGIN":
                active = True
                continue
            if line == "LED_DUMP_END":
                break
            if active and ":" in line:
                key, _, val = line.partition(":")
                data[key] = val

    if not active:
        raise RuntimeError(
            "Board did not send LED_DUMP_BEGIN.\n"
            "Make sure the firmware includes the led_dump command."
        )
    return data


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_rgb(s):
    """'RRGGBBRRGGBB...' → list of (r,g,b) tuples."""
    out = []
    for i in range(0, len(s) - 5, 6):
        chunk = s[i:i+6]
        try:
            r, g, b = int(chunk[0:2], 16), int(chunk[2:4], 16), int(chunk[4:6], 16)
        except ValueError:
            r, g, b = 0, 0, 0
        out.append((r, g, b))
    return out


def pad(lst, length, default):
    while len(lst) < length:
        lst.append(default)


# ── Rendering ─────────────────────────────────────────────────────────────────

_RESET = "\x1b[0m"

def _cell(r, g, b, is_ep):
    """Two-character ANSI cell.  ◆ marks endpoints."""
    if r == 0 and g == 0 and b == 0:
        return f"\x1b[48;2;18;18;18m· {_RESET}"
    ch = "◆ " if is_ep else "  "
    return f"\x1b[48;2;{r};{g};{b}m{ch}{_RESET}"


def render(path_rgb, end_rgb, ep_flags):
    eff = [end_rgb[i] if ep_flags[i] else path_rgb[i] for i in range(NUM_LEDS)]

    lines = []

    def section(label, row_labels, cols, col_offset, index_fn):
        """
        row_labels : list of strings, one per row  (e.g. ['+', '-'] or ['a'..'e'])
        cols       : number of columns to render
        col_offset : added to col index for the header label (1 for 1-indexed display)
        index_fn   : (row, col) -> strip index
        """
        lines.append(f"\n  {label}")
        # Header: 6-char prefix to match "  X │" row prefix, then col labels
        hdr = "      "                          # 6 spaces — matches "  X │" width
        for c in range(cols):
            disp = c + col_offset
            hdr += f"{disp:<2}" if (disp == 1 or disp % 5 == 0) else "  "
        lines.append(hdr)
        for ri, rl in enumerate(row_labels):
            row_s = f"  {rl:>2} │"              # "  a │" — 6 chars
            for col in range(cols):
                idx = index_fn(ri, col)
                r, g, b = eff[idx]
                row_s += _cell(r, g, b, ep_flags[idx])
            lines.append(row_s)

    section("TOP RAILS (2×25)",    ["+", "-"], 25, 1, top_rail_index)
    section("MID1 (5×30)",         list("abcde"), 30, 1, mid1_index)
    section("MID2 (5×30)",         list("fghij"), 30, 1, mid2_index)
    section("BOTTOM RAILS (2×25)", ["+", "-"], 25, 1, bottom_rail_index)

    active_count = sum(1 for c in eff if c != (0, 0, 0))
    ep_count     = sum(ep_flags)
    lines.append(f"\n  Active: {active_count}   Endpoints: {ep_count}")

    # Detail table (only when few LEDs active — easy to read)
    if 0 < active_count <= 60:
        lines.append("")
        lines.append("  Active LED index  →  colour")
        for i, c in enumerate(eff):
            if c == (0, 0, 0):
                continue
            r, g, b = c
            mark = "  [EP]" if ep_flags[i] else ""
            lines.append(f"    LED {i:>3}  #{r:02X}{g:02X}{b:02X}{mark}")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="JumperZ LED Matrix Debug Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--port",     help="Serial port (auto-detected if omitted)")
    ap.add_argument("--baud",     type=int, default=115200)
    ap.add_argument("--loop",     action="store_true", help="Refresh continuously")
    ap.add_argument("--interval", type=float, default=1.0, help="Refresh interval (s)")
    ap.add_argument("--raw",      action="store_true",
                    help="Print raw hex lines and exit (useful for sharing)")
    args = ap.parse_args()

    port = args.port
    if not port:
        _, bridge = find_ports()
        if not bridge:
            print("ERROR: JumperZ board not found.  Connect the board or use --port COM#")
            sys.exit(1)
        port = bridge
        print(f"Using bridge port: {port}")

    first = True
    while True:
        try:
            raw = fetch_dump(port, args.baud)

            if args.raw:
                for k, v in raw.items():
                    print(f"{k}:{v}")
                return

            path_rgb = parse_rgb(raw.get("PATH", ""))
            end_rgb  = parse_rgb(raw.get("ENDP", ""))
            ep_str   = raw.get("EP", "")
            ep_flags = [c == "1" for c in ep_str]

            pad(path_rgb, NUM_LEDS, (0, 0, 0))
            pad(end_rgb,  NUM_LEDS, (0, 0, 0))
            pad(ep_flags, NUM_LEDS, False)

            if args.loop and not first:
                print("\x1b[2J\x1b[H", end="", flush=True)

            ts = time.strftime("%H:%M:%S")
            print(f"=== JumperZ LED Matrix  {ts} {'[LOOP]' if args.loop else ''} ===")
            print(render(path_rgb, end_rgb, ep_flags))
            first = False

        except KeyboardInterrupt:
            print("\nAborted.")
            break
        except Exception as exc:
            print(f"ERROR: {exc}")
            if not args.loop:
                sys.exit(1)

        if not args.loop:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
