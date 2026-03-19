#!/usr/bin/env python3
"""
current_viz.py — Toggle animated current-flow visualization on JumperZ.

The firmware automatically determines current direction by propagating known
supply voltages through the connected nets:
  GND (node 100) = 0 V,  3.3V (node 103) = 3.3 V,  5V (node 105) = 5.0 V

For a circuit like  5V --- Resistor --- LED(A)---LED(C) --- GND:
  - Nodes connected to 5V get potential 5 V
  - Nodes connected to GND get potential 0 V
  - The spark on each wire travels from the high-potential end to the low end
    → conventional current direction (positive to negative)

If a wire can't be traced to any supply (e.g. powered from a Nano pin),
the animation falls back to bidirectional so something is always visible.

Usage:
  python current_viz.py --on               # enable at default speed
  python current_viz.py --on --speed 2.0   # double speed
  python current_viz.py --off              # disable, restore static frame
  python current_viz.py                    # interactive toggle

Typical workflow:
  1. Connect a circuit:  python main.py  (or send {"cmd":"connect",...})
  2. Enable viz:         python current_viz.py --on
  3. Disable:            python current_viz.py --off
"""

import argparse
import sys

from measure import BoardConn


def set_viz(conn: BoardConn, enable: bool, speed: float = 1.0) -> None:
    resp = conn.send({"cmd": "current_viz", "enable": enable, "speed": speed})
    if resp.get("ok"):
        state = "ON " if enable else "OFF"
        print(f"current_viz: {state}  speed={resp.get('speed', speed):.1f}")
    else:
        print(f"Error: {resp}", file=sys.stderr)


def interactive(conn: BoardConn, speed: float) -> None:
    state = False
    print("current_viz interactive — Enter=toggle, +/-=speed, q=quit")
    while True:
        label = "ON " if state else "OFF"
        try:
            inp = input(f"  [{label}  speed={speed:.1f}]  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if inp in ("q", "quit", "exit"):
            break
        elif inp in ("+", "f", "faster"):
            speed = min(speed + 0.5, 10.0)
            print(f"  speed → {speed:.1f}")
            if state:
                set_viz(conn, True, speed)
        elif inp in ("-", "s", "slower"):
            speed = max(speed - 0.5, 0.1)
            print(f"  speed → {speed:.1f}")
            if state:
                set_viz(conn, True, speed)
        else:
            state = not state
            set_viz(conn, state, speed)

    if state:
        set_viz(conn, False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Toggle JumperZ current-flow LED animation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--on",  action="store_true", help="Enable animation")
    grp.add_argument("--off", action="store_true", help="Disable, restore static frame")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Speed multiplier (default 1.0 ≈ 750 ms per cycle)")
    args = parser.parse_args()

    try:
        conn = BoardConn()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.on:
        set_viz(conn, True, args.speed)
    elif args.off:
        set_viz(conn, False)
    else:
        interactive(conn, args.speed)


if __name__ == "__main__":
    main()
