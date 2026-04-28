#!/usr/bin/env python3
"""
probe_connect.py — Route oscilloscope probes & function-generator outputs
to any breadboard / nano / external-header node on the JumperZ board.

The board exposes 6 dedicated pins on Chip K of the CH446Q crosspoint matrix:

  Probe              Chip K X   sfMappings name(s)              Default color
  ─────────────────  ────────   ──────────────────────────────  ─────────────
  Master scope        X8        OSC_PROBE      / MASTER_PROBE   cyan
  External GND clip   X9        EXT_GND        / EXTERNAL_GND   grey
  Square wave  (FG)   X10       SQUARE_WAVE_FUN/ SQUARE_WAVE    orange
  Sine/triangle (FG)  X11       SINE_TRANG_FUN / SINE_WAVE      magenta
  3.3V-range probe    X12       PROBE_3V3      / EXTRA_1        green
  5V-range probe      X13       PROBE_5V       / EXTRA_2        red

By default the external-GND clip is auto-tied to the on-board GND rail. If
you also want to clip ext-GND onto a specific board node, pass `--ext-gnd
NODE` — the NODE, GND and the EXT_GND pin all join one net. Pass
`--no-ext-gnd` to skip the auto-GND tie entirely.

This tool uses the {"cmd":"probe_connect"} JSON command, which is
NON-DESTRUCTIVE: existing user nets created by main.py / connect.py keep
their LED paint and CH446Q routing. Each probe_connect call replaces the
PREVIOUSLY-routed probes (so it doesn't accumulate stale ones) but never
touches any other user net.

Usage examples
--------------
  # Just the master probe on TOP_5 (your main.py paths stay lit)
  python probe_connect.py --master TOP_5

  # Function-gen square wave to BOTTOM_3, scope master to TOP_5
  python probe_connect.py --square BOTTOM_3 --master TOP_5

  # Tie ext-GND clip to TOP_15 (it stays tied to GND too)
  python probe_connect.py --master TOP_5 --ext-gnd TOP_15

  # Skip the auto ext-GND-to-GND tie
  python probe_connect.py --master TOP_5 --no-ext-gnd

  # Full setup
  python probe_connect.py --master TOP_5 --3v3 TOP_8 --5v TOP_12 \
                          --square BOTTOM_3 --sine BOTTOM_5

  # Add an extra net alongside the probes (also non-destructive — replaces
  # the previously-routed extras, leaves main.py nets alone)
  python probe_connect.py --master TOP_5 --extra TOP_10 BOTTOM_10

  # Disconnect probes only (main.py paths stay)
  python probe_connect.py --clear

  # Disconnect EVERYTHING (probes + main.py paths) — full board wipe
  python probe_connect.py --clear-all

  # Show currently committed paths
  python probe_connect.py --list
"""

import argparse
import json
import sys
import time

import serial
import serial.tools.list_ports


# ── Probe descriptors ────────────────────────────────────────────────────────
# (cli flag, argparse dest, sfMappings node name, hex color, friendly label)
PROBES = [
    ("--master", "master", "OSC_PROBE",       "#00FFFF", "Master scope"),
    ("--3v3",    "p3v3",   "PROBE_3V3",       "#00FF66", "3.3V-range probe"),
    ("--5v",     "p5v",    "PROBE_5V",        "#FF3030", "5V-range probe"),
    ("--square", "square", "SQUARE_WAVE_FUN", "#FF8000", "Function-gen square"),
    ("--sine",   "sine",   "SINE_TRANG_FUN",  "#FF00FF", "Function-gen sine/tri"),
]

EXT_GND_NAME  = "EXT_GND"
EXT_GND_COLOR = "#888888"


# ── Port detection (mirrors settings_tool.py) ───────────────────────────────
VID_TOKEN = "1D51"
PID_TOKEN = "ACAB"
BRIDGE_LOC_SUFFIX = "X.2"


def _upper(x: str) -> str:
    return (x or "").upper()


def _loc_suffix(hwid: str) -> str | None:
    h = _upper(hwid)
    key = "LOCATION="
    i = h.find(key)
    if i < 0:
        return None
    loc = h[i + len(key):].strip()
    return loc.split(":")[-1].strip() if ":" in loc else loc


def find_bridge_port() -> str | None:
    for p in serial.tools.list_ports.comports():
        hwid = _upper(getattr(p, "hwid", ""))
        if VID_TOKEN not in hwid or PID_TOKEN not in hwid:
            continue
        if _loc_suffix(hwid) == BRIDGE_LOC_SUFFIX:
            return p.device
    return None


# ── Board connection ────────────────────────────────────────────────────────
class BoardConn:
    def __init__(self, baud: int = 115200, timeout: float = 5.0):
        port = find_bridge_port()
        if not port:
            raise RuntimeError(
                "JumperZ bridge port (JZ NETSH) not found.\n"
                "Is the board plugged in and the USB cable data-capable?"
            )
        self.port = port
        self._s = serial.Serial(port, baudrate=baud, timeout=timeout, write_timeout=2)
        time.sleep(0.15)  # Windows CDC settle

    def __enter__(self):  return self
    def __exit__(self, *a): self.close()

    def send(self, payload: dict) -> dict:
        line = json.dumps(payload, separators=(",", ":")) + "\n"
        self._s.write(line.encode("utf-8"))
        raw = self._s.readline()
        if not raw:
            raise TimeoutError("No response from board (timeout).")
        return json.loads(raw.decode("utf-8").strip())

    def close(self):
        try:
            self._s.close()
        except Exception:
            pass


# ── Core operations ─────────────────────────────────────────────────────────

def collect_nets(args) -> list[dict]:
    """Build the nets[] payload from CLI args. Returns [] when no probes set."""
    nets: list[dict] = []

    # Probe nets — one per requested probe
    for _, dest, node_name, color, label in PROBES:
        target = getattr(args, dest)
        if target:
            nets.append({
                "nodes": [node_name, target],
                "color": color,
                "_label": label,                # internal — stripped before send
            })

    # External GND handling
    if args.no_ext_gnd:
        if args.ext_gnd:
            print("warning: --ext-gnd ignored because --no-ext-gnd is set",
                  file=sys.stderr)
    else:
        ext_nodes = [EXT_GND_NAME, "GND"]
        if args.ext_gnd:
            ext_nodes.append(args.ext_gnd)
        nets.append({
            "nodes": ext_nodes,
            "color": EXT_GND_COLOR,
            "_label": "External GND",
        })

    # User-supplied extra nets (each --extra wants ≥2 nodes)
    for i, group in enumerate(args.extra or []):
        if len(group) < 2:
            print(f"error: --extra group #{i + 1} needs at least two nodes "
                  f"(got {group})", file=sys.stderr)
            sys.exit(1)
        nets.append({
            "nodes": group,
            "color": "#FFFFFF",
            "_label": "extra",
        })

    return nets


def run_connect(conn: BoardConn, nets: list[dict]) -> None:
    """Send the nets via {"cmd":"probe_connect"} (non-destructive) and
    pretty-print the result."""
    # Strip the internal _label keys before sending (firmware ignores them
    # but keeping the JSON small is polite).
    payload_nets = [{k: v for k, v in n.items() if k != "_label"} for n in nets]
    payload = {"cmd": "probe_connect", "nets": payload_nets}

    resp = conn.send(payload)
    ok          = resp.get("ok")
    nets_added  = resp.get("nets_added", 0)
    paths       = resp.get("paths", 0)
    skipped     = resp.get("skipped", 0)
    err_nodes   = resp.get("err_nodes", [])

    print(f"\nConnected on {conn.port}")
    print("─" * 56)
    if ok:
        for n in nets:
            label = n.get("_label", "net")
            nodes = " ↔ ".join(n["nodes"])
            print(f"  {label:<22}  {nodes}")
        print("─" * 56)
        print(f"  nets_added (probes) : {nets_added}")
        print(f"  total paths         : {paths}")
        if skipped:
            print(f"  skipped             : {skipped}")
        if err_nodes:
            print(f"  err_nodes           : {err_nodes}  ← unknown to firmware sfMappings")
    else:
        print(f"  ERROR: {resp}")
        sys.exit(1)


def run_clear_probes(conn: BoardConn) -> None:
    """Probe-only clear: free probe slots, leave the rest of the netlist alone."""
    resp = conn.send({"cmd": "probe_connect", "nets": []})
    if resp.get("ok"):
        print("Probes cleared. Other user nets (e.g. main.py paths) untouched.")
    else:
        print(f"probe_connect clear failed: {resp}", file=sys.stderr)
        sys.exit(1)


def run_clear_all(conn: BoardConn) -> None:
    """Full board wipe: probes + every user net + LEDs."""
    resp = conn.send({"cmd": "clear"})
    if resp.get("ok"):
        print("All connections cleared (LEDs off, CH446Q reset).")
    else:
        print(f"clear failed: {resp}", file=sys.stderr)
        sys.exit(1)


def run_list(conn: BoardConn) -> None:
    resp = conn.send({"cmd": "netlist_query"})
    if not resp.get("ok"):
        print(f"netlist_query failed: {resp}", file=sys.stderr)
        sys.exit(1)
    paths = resp.get("paths", 0)
    items = resp.get("list", [])
    print(f"\nCommitted paths on {conn.port}: {paths}")
    print("─" * 56)
    if not items:
        print("  (none)")
        return
    print(f"  {'i':>3}  {'net':>3}  {'type':>4}  {'n1':>4} {'n2':>4}  "
          f"{'c0':>3} {'c1':>3}  alt")
    for p in items:
        print(f"  {p.get('i',0):>3}  {p.get('net',0):>3}  "
              f"{p.get('type',0):>4}  {p.get('n1',0):>4} {p.get('n2',0):>4}  "
              f"{p.get('c0',-1):>3} {p.get('c1',-1):>3}  "
              f"{'Y' if p.get('alt') else '-'}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Route JumperZ oscilloscope / function-gen probes to any node.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    for flag, dest, _, _, label in PROBES:
        ap.add_argument(flag, dest=dest, metavar="NODE", default=None,
                        help=f"Connect {label} to NODE (e.g. TOP_5, "
                             f"BOTTOM_14, NANO_D3)")

    ap.add_argument("--ext-gnd", dest="ext_gnd", metavar="NODE", default=None,
                    help="Tie ext-GND probe to NODE (it also stays tied to GND).")
    ap.add_argument("--no-ext-gnd", action="store_true",
                    help="Don't auto-connect the ext-GND probe to GND.")
    ap.add_argument("--extra", nargs="+", action="append", metavar="NODE",
                    help="Add an arbitrary net (≥2 nodes). Repeatable. "
                         "Useful for wiring circuits alongside probes since "
                         "this command is destructive.")
    ap.add_argument("--clear", action="store_true",
                    help="Disconnect probes only (preserves other user nets).")
    ap.add_argument("--clear-all", dest="clear_all", action="store_true",
                    help="Full board wipe: probes + every user net + LEDs.")
    ap.add_argument("--list", dest="list_paths", action="store_true",
                    help="Show currently committed paths and exit.")
    return ap


def main():
    args = _build_parser().parse_args()

    # --list / --clear / --clear-all / probe args are mutually exclusive.
    op_count = sum(bool(x) for x in (args.list_paths, args.clear, args.clear_all))
    has_probes = (any(getattr(args, dest) for _, dest, *_ in PROBES)
                  or args.ext_gnd or args.extra)
    if op_count > 1 or (op_count == 1 and has_probes):
        print("error: --clear / --clear-all / --list / probe options are "
              "mutually exclusive", file=sys.stderr)
        sys.exit(2)

    if op_count == 0 and not has_probes:
        # Nothing actionable on the command line — print help and exit.
        # (--no-ext-gnd alone is not enough; we need at least one probe
        # or a --clear / --clear-all / --list to do anything useful.)
        _build_parser().print_help()
        sys.exit(0)

    try:
        with BoardConn() as conn:
            if args.list_paths:
                run_list(conn)
            elif args.clear_all:
                run_clear_all(conn)
            elif args.clear:
                run_clear_probes(conn)
            else:
                nets = collect_nets(args)
                if not nets:
                    print("error: no probes selected; nothing to do.",
                          file=sys.stderr)
                    sys.exit(2)
                run_connect(conn, nets)
    except (RuntimeError, TimeoutError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
