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

Bridges whose direction cannot be resolved (isolated from all supplies) are
skipped — no bidirectional fallback.  Only valid direction bridges animate.

Usage:
  python current_viz.py               # auto-detect all flows and start
  python current_viz.py --auto        # same as above (explicit)
  python current_viz.py --auto --speed 2.0
  python current_viz.py --on          # enable at default speed (no display)
  python current_viz.py --off         # disable, restore static frame
  python current_viz.py --select      # pick specific segments interactively
  python current_viz.py --interactive # interactive toggle menu

Auto mode example output:
  Querying netlist ...

  Detected current flows:
  ─────────────────────────────────────────────────────────────
  [direct]  5V          →  TOP_5          (net 8)
  [direct]  TOP_10      →  GND            (net 8)
  [prop  ]  TOP_5       ~  TOP_10         (net 8)  ← direction via propagation

  Animation started — 3 bridge(s), speed 1.0
"""

import argparse
import sys

from measure import BoardConn
from node_map import name as node_name

# Known supply node numbers (mirrors pin_map.h)
_GND  = 100
_3V3  = 103
_5V   = 105
_DAC0 = 106
_DAC1 = 107

_POSITIVE_SUPPLIES = (_3V3, _5V, _DAC0, _DAC1)


# ── Netlist helpers ───────────────────────────────────────────────────────────

def query_bridges(conn: BoardConn) -> list[dict]:
    """
    Query the active netlist and return deduplicated logical bridges.
    Each entry: {"n1": int, "n2": int, "net": int}
    """
    resp = conn.send({"cmd": "netlist_query"})
    if not resp.get("ok"):
        print(f"  Warning: netlist_query failed: {resp.get('err', resp)}")
        return []

    seen: set[tuple[int, int]] = set()
    bridges: list[dict] = []
    for p in resp.get("list", []):
        n1, n2, net_idx = int(p["n1"]), int(p["n2"]), int(p["net"])
        if n1 == 0 or n2 == 0:
            continue
        key = (min(n1, n2), max(n1, n2))
        if key in seen:
            continue
        seen.add(key)
        bridges.append({"n1": n1, "n2": n2, "net": net_idx})

    return bridges


def _infer_direction(n1: int, n2: int) -> tuple[int, int] | None:
    """
    Infer current direction from node numbers alone (no firmware query needed).
    Returns (from_node, to_node) when direction is certain, None when it
    requires voltage propagation (breadboard-to-breadboard wires).

    Rules:
      Positive supply (5V/3V3/DAC): current flows away from supply node.
      GND: current flows toward GND node.
    """
    if n1 in _POSITIVE_SUPPLIES:
        return (n1, n2)
    if n2 in _POSITIVE_SUPPLIES:
        return (n2, n1)
    if n1 == _GND:
        return (n2, n1)
    if n2 == _GND:
        return (n1, n2)
    return None   # need propagation — firmware handles this


# ── Auto mode ─────────────────────────────────────────────────────────────────

def auto_viz(conn: BoardConn, speed: float) -> None:
    """
    Auto-detect all valid current-flow directions, print them, and start
    the animation for every bridge.  The firmware's voltage-propagation logic
    determines direction for breadboard-to-breadboard bridges; the comet
    travels strictly over pixels that paintBridgeLeds() actually painted.
    """
    print("  Querying netlist ...")
    bridges = query_bridges(conn)

    if not bridges:
        print("  No active bridges found.")
        print("  Connect a circuit first (e.g. python main.py).")
        return

    # Classify bridges
    direct: list[dict]     = []   # direction deterministic from node type
    propagated: list[dict] = []   # direction needs firmware propagation

    for b in bridges:
        d = _infer_direction(b["n1"], b["n2"])
        if d is not None:
            direct.append({**b, "from": d[0], "to": d[1]})
        else:
            propagated.append(b)

    # Display
    print()
    print("  Detected current flows:")
    print("  " + "─" * 62)

    if not direct and not propagated:
        print("  (none)")
    else:
        for b in direct:
            fn = node_name(b["from"])
            tn = node_name(b["to"])
            print(f"  [direct]  {fn:<14} ->  {tn:<14}  (net {b['net']})")
        for b in propagated:
            n1s = node_name(b["n1"])
            n2s = node_name(b["n2"])
            print(f"  [prop  ]  {n1s:<14} ~   {n2s:<14}  (net {b['net']})"
                  "  <- direction via propagation")

    print()

    # Start animation — no bridge filter, firmware handles direction detection
    # and only animates bridges with a resolvable flow direction.
    resp = conn.send({"cmd": "current_viz", "enable": True, "speed": speed})
    if resp.get("ok"):
        total = len(direct) + len(propagated)
        print(f"  Animation started — {total} bridge(s), speed {speed:.1f}")
        print("  (firmware animates only bridges with resolved current direction)")
        print("  Press Ctrl-C to stop.")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print()
            set_viz(conn, False)
    else:
        print(f"  Error: {resp}", file=sys.stderr)


# ── Segment-selection interactive menu ───────────────────────────────────────

def _pick_bridges(bridges: list[dict]) -> list[dict] | None:
    """
    Show numbered bridge list and return the user's selection.
      None  → animate ALL bridges (no filter)
      []    → user quit / disable
      [...]  → specific bridges to animate
    """
    if not bridges:
        print("  No active bridges on the board.")
        print("  Connect a circuit first with the 'connect' command.")
        return []

    print()
    print("  Active bridges:")
    print("  " + "─" * 54)
    for i, b in enumerate(bridges):
        n1s = node_name(b["n1"])
        n2s = node_name(b["n2"])
        d = _infer_direction(b["n1"], b["n2"])
        if d is not None:
            arrow = f"{node_name(d[0])} -> {node_name(d[1])}"
        else:
            arrow = f"{n1s} ~ {n2s}"
        print(f"  [{i + 1:2}]  {arrow:<32}  (net {b['net']})")
    print()
    print("  [A]  All bridges (no filter)")
    print("  [Q]  Quit / disable")
    print()

    while True:
        try:
            raw = input("  Select (e.g.  1  or  1,3  or  A): ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print()
            return []

        if raw in ("Q", "QUIT", "EXIT"):
            return []
        if raw in ("A", "ALL", ""):
            return None

        try:
            indices = [int(x.strip()) - 1 for x in raw.split(",")]
            selected = []
            ok = True
            for idx in indices:
                if 0 <= idx < len(bridges):
                    selected.append(bridges[idx])
                else:
                    print(f"  '{idx + 1}' out of range.")
                    ok = False
            if ok and selected:
                return selected
        except ValueError:
            pass
        print("  Invalid input — try again.")


def segment_select(conn: BoardConn, speed: float) -> None:
    """Interactive segment-selection mode."""
    print("  Querying netlist ...")
    bridges = query_bridges(conn)
    selected = _pick_bridges(bridges)

    if selected == []:
        set_viz(conn, False)
        return

    if selected is None:
        # Animate everything
        set_viz(conn, True, speed)
        return

    # Build [[n1,n2], ...] pair list for the firmware filter
    pairs = [[b["n1"], b["n2"]] for b in selected]
    resp = conn.send({
        "cmd": "current_viz",
        "enable": True,
        "speed": speed,
        "bridges": pairs,
    })

    if resp.get("ok"):
        n = resp.get("filter_pairs", len(pairs))
        print(f"  Animating {n} segment(s):")
        for b in selected:
            d = _infer_direction(b["n1"], b["n2"])
            if d is not None:
                print(f"    -> {node_name(d[0])} -> {node_name(d[1])}")
            else:
                print(f"    ~  {node_name(b['n1'])} ~ {node_name(b['n2'])}  (propagated)")
        print(f"  Speed: {speed:.1f}")
    else:
        print(f"  Error: {resp}", file=sys.stderr)


# ── Basic helpers ─────────────────────────────────────────────────────────────

def set_viz(conn: BoardConn, enable: bool, speed: float = 1.0) -> None:
    resp = conn.send({"cmd": "current_viz", "enable": enable, "speed": speed})
    if resp.get("ok"):
        state = "ON " if enable else "OFF"
        print(f"current_viz: {state}  speed={resp.get('speed', speed):.1f}")
    else:
        print(f"Error: {resp}", file=sys.stderr)


def interactive(conn: BoardConn, speed: float) -> None:
    state = False
    print("current_viz interactive — Enter=toggle, +/-=speed, s=select segments, q=quit")
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
            print(f"  speed -> {speed:.1f}")
            if state:
                set_viz(conn, True, speed)
        elif inp in ("-", "slower"):
            speed = max(speed - 0.5, 0.1)
            print(f"  speed -> {speed:.1f}")
            if state:
                set_viz(conn, True, speed)
        elif inp in ("sel", "select", "seg", "segments"):
            segment_select(conn, speed)
            state = True
        else:
            state = not state
            set_viz(conn, state, speed)

    if state:
        set_viz(conn, False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="JumperZ current-flow LED animation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--auto",        action="store_true",
                     help="Auto-detect all current flows and animate (default)")
    grp.add_argument("--on",          action="store_true",
                     help="Enable animation (no display)")
    grp.add_argument("--off",         action="store_true",
                     help="Disable animation, restore static frame")
    grp.add_argument("--select",      action="store_true",
                     help="Interactively pick which bridges to animate")
    grp.add_argument("--interactive", action="store_true",
                     help="Interactive toggle menu")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Speed multiplier (default 1.0 ~= 750 ms per cycle)")
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
    elif args.select:
        segment_select(conn, args.speed)
    elif args.interactive:
        interactive(conn, args.speed)
    else:
        # Default (no flag, or --auto): auto-detect and animate
        auto_viz(conn, args.speed)


if __name__ == "__main__":
    main()
