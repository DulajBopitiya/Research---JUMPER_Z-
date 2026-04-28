#!/usr/bin/env python3
"""
measure.py — JumperZ INA219 voltage / current measurement tool.

INA219 connection via Chip L crosspoint:
  Chip L X0 = ISENSE_MINUS = IN−  ← bus voltage measured here (V(node))
  Chip L X1 = ISENSE_PLUS  = IN+  ← shunt high-side

Voltage mode  (default):  node → ISENSE_MINUS  → bus_v = V(node)
Diff mode     (--node2):  two-pass: measure V(node) then V(node2) via bus-V ADC
                           → node_v = V(node vs GND), node2_v = V(node2 vs GND)
                           → diff_v = node2_v − node_v
                           Range: 0–32 V, resolution: 4 mV. No ±320 mV limit.
Current mode  (--plus):   plus → ISENSE_PLUS, node → ISENSE_MINUS
                           → bus_v = V(node), current_ma = shunt_mV / R_shunt

Usage:
  python measure.py TOP_17                          single voltage reading
  python measure.py TOP_17 -c                       continuous voltage (Ctrl+C)
  python measure.py TOP_17 -c --interval 0.2        faster loop
  python measure.py TOP_17 --node2 TOP_14           differential: V(TOP_14)−V(TOP_17)
  python measure.py TOP_17 --node2 TOP_14 -c        continuous differential
  python measure.py TOP_17 --plus 5V                current measurement
  python measure.py TOP_17 --plus 5V -c             continuous current
  python measure.py TOP_17 --plus 5V --guided       two-pass: baseline then load
  python measure.py TOP_17 --plus 5V --autodiff     auto-detect toggling signals
  python measure.py --clear                         restore netlist brightness
  python measure.py -i                              interactive menu
"""

import argparse
import json
import sys
import time

import serial
import serial.tools.list_ports

from bridge_send import find_ports


# ---------------------------------------------------------------------------
# Persistent board connection
# ---------------------------------------------------------------------------

class BoardConn:
    def __init__(self, baud: int = 115200, timeout: float = 3.0):
        _, bridge = find_ports()
        if not bridge:
            raise RuntimeError(
                "JumperZ bridge port (JZ NETSH) not found.\n"
                "Is the board plugged in?"
            )
        self._s = serial.Serial(bridge, baudrate=baud,
                                timeout=timeout, write_timeout=2)
        time.sleep(0.15)   # Windows CDC settle

    def send(self, payload: dict) -> dict:
        line = json.dumps(payload, separators=(",", ":")) + "\n"
        self._s.write(line.encode("utf-8"))
        self._s.flush()
        resp_bytes = self._s.readline()
        if not resp_bytes:
            raise RuntimeError("No response from board (timeout).")
        return json.loads(resp_bytes.decode("utf-8", errors="replace").strip())

    def close(self):
        if self._s and self._s.is_open:
            self._s.close()

    def __enter__(self):  return self
    def __exit__(self, *_): self.close()


# ---------------------------------------------------------------------------
# Board commands
# ---------------------------------------------------------------------------

def _measure(conn: BoardConn, node: str,
             plus: str = None, node2: str = None, sensor: int = 0) -> dict:
    """Single-node voltage or current measurement.
    If node2 is provided, uses measure_diff (two-pass bus-voltage, 0–32V range).
    If plus is provided, uses current mode (shunt register).
    """
    if node2:
        # Two-pass absolute differential: not limited to ±320mV shunt range
        payload = {"cmd": "measure_diff",
                   "node": node.upper(), "node2": node2.upper(), "sensor": sensor}
    else:
        payload = {"cmd": "measure", "node": node.upper(), "sensor": sensor}
        if plus:
            payload["plus"] = plus.upper()
    return conn.send(payload)


def _measure_clear(conn: BoardConn) -> dict:
    return conn.send({"cmd": "measure_clear"})


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _mode_label(resp: dict) -> str:
    return resp.get("mode", "voltage")


def _print_full(resp: dict):
    if not resp.get("ok"):
        print(f"  ERROR: {resp.get('err', '?')}  (node={resp.get('node')})")
        return

    mode = _mode_label(resp)
    if mode == "diff":
        method = resp.get("method", "shunt")
        twopass = (method == "twopass")
        print(f"\n  Node      : {resp['node']}   (reference)")
        print(f"  Node2     : {resp['node2']}   (measured)")
        print(f"  Sensor    : INA219 #{resp['sensor']}  [diff — {'two-pass bus-V' if twopass else 'shunt register ±320mV'}]")
        print(f"  {'─'*44}")
        node_v  = float(resp['node_v'])
        node2_v = float(resp['node2_v'])
        diff_mv = float(resp['diff_mv'])
        diff_v  = float(resp.get('diff_v', diff_mv / 1000.0))
        print(f"  V({resp['node']:<12}) : {node_v:>10.4f}  V")
        print(f"  V({resp['node2']:<12}) : {node2_v:>10.4f}  V")
        print(f"  ΔV (node2−node)  : {diff_v:>10.4f}  V  ({diff_mv:+.2f} mV)")
        if not twopass:
            print(f"  NOTE: shunt register ±320 mV limit — use measure_diff for large drops")
        print()
        return

    print(f"\n  Node      : {resp['node']}")
    if mode == "current":
        print(f"  Plus      : {resp.get('plus','')}  →  ISENSE+")
        print(f"  Node      :  above       →  ISENSE−")
    print(f"  Sensor    : INA219 #{resp['sensor']}  [{mode} mode]")
    print(f"  {'─'*38}")
    print(f"  Voltage   : {float(resp['bus_v']):>10.4f}  V")
    if mode == "current":
        print(f"  Shunt     : {float(resp['shunt_mv']):>10.4f}  mV")
        print(f"  Current   : {float(resp['current_ma']):>10.4f}  mA")
        print(f"  Power     : {float(resp['power_mw']):>10.4f}  mW")
    print()


# Compact header and row for continuous / table output
_HDR_V = "  {:<12}  {:>12}  {:>8}"
_ROW_V = "  {:<12}  {:>10.4f} V  {:>6}"

_HDR_I = "  {:<12}  {:>12}  {:>12}  {:>12}  {:>12}"
_ROW_I = "  {:<12}  {:>10.4f} V  {:>9.4f}mV  {:>9.4f}mA  {:>9.4f}mW"

_HDR_D = "  {:<12}  {:<12}  {:>12}  {:>12}  {:>12}"
_ROW_D = "  {:<12}  {:<12}  {:>9.4f} V  {:>9.4f} V  {:>+9.4f}mV"


def _print_header(mode: str):
    if mode == "current":
        print(_HDR_I.format("Node", "Voltage", "Shunt mV", "Current mA", "Power mW"))
        print("  " + "-" * 72)
    elif mode == "diff":
        print(_HDR_D.format("Node", "Node2", "V(node)", "V(node2)", "ΔV (mV)"))
        print("  " + "-" * 72)
    else:
        print(_HDR_V.format("Node", "Voltage", ""))
        print("  " + "-" * 36)


def _print_row(resp: dict, count: int):
    if not resp.get("ok"):
        print(f"[{count:>4}]  ERROR: {resp.get('err','?')}")
        return
    mode = _mode_label(resp)
    prefix = f"[{count:>4}] "
    if mode == "current":
        print(prefix + _ROW_I.format(
            resp["node"],
            float(resp["bus_v"]),
            float(resp["shunt_mv"]),
            float(resp["current_ma"]),
            float(resp["power_mw"]),
        ))
    elif mode == "diff":
        diff_mv = float(resp["diff_mv"])
        diff_v  = float(resp.get("diff_v", diff_mv / 1000.0))
        print(prefix + _ROW_D.format(
            resp["node"],
            resp["node2"],
            float(resp["node_v"]),
            float(resp["node2_v"]),
            diff_mv,
        ))
    else:
        print(prefix + _ROW_V.format(
            resp["node"],
            float(resp["bus_v"]),
            "",
        ))


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def do_single(conn, node, plus=None, node2=None, sensor=0, as_json=False):
    resp = _measure(conn, node, plus=plus, node2=node2, sensor=sensor)
    if as_json:
        print(json.dumps(resp, indent=2))
    else:
        _print_full(resp)
    return resp.get("ok", False)


def do_continuous(conn, node, plus=None, node2=None, sensor=0, interval=0.5):
    mode = "diff" if node2 else ("current" if plus else "voltage")
    desc = f"node={node!r}"
    if node2:
        desc += f"  node2={node2!r}"
    elif plus:
        desc += f"  plus={plus!r}"
    print(f"  Continuous — {desc}  sensor={sensor}  interval={interval}s")
    print(f"  Ctrl+C to stop (netlist will be restored automatically)\n")

    _print_header(mode)
    count = 0
    try:
        while True:
            resp = _measure(conn, node, plus=plus, node2=node2, sensor=sensor)
            count += 1
            _print_row(resp, count)
            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n  Stopped after {count} reading(s).")


def do_guided(conn, node: str, plus: str | None, sensor: int):
    """
    Two-pass guided measurement.
      Pass 1: measure without external load  → baseline (path leakage)
      Pass 2: user connects load, measure again
      Report: net load current = total − baseline, corrected voltage
    """
    sep = "  " + "─" * 52

    print(f"\n  Guided measurement")
    print(f"  Node   : {node}    Plus : {plus or '(voltage only)'}    Sensor : {sensor}")
    print(sep)

    # ── Pass 1 ──────────────────────────────────────────────────────────────
    print(f"\n  Step 1 / 2 — Baseline  (nothing connected to {node!r})")
    print(f"  Disconnect any external load from this node now.")
    input("  Press Enter when ready… ")

    b = _measure(conn, node, plus, sensor)
    if not b.get("ok"):
        print(f"  ERROR: {b.get('err', '?')}")
        return

    V_base = float(b["bus_v"])
    I_base = float(b.get("current_ma", 0.0))
    S_base = float(b.get("shunt_mv", 0.0))

    print(f"  Baseline → V = {V_base:.4f} V   I = {I_base:.4f} mA   Shunt = {S_base:.4f} mV")

    # Estimate CH446Q Ron from baseline (supply − bus) / I
    if plus and I_base > 0.01:
        v_supply = {"5V": 5.0, "+5V": 5.0, "3V3": 3.3, "+3.3V": 3.3,
                    "3.3V": 3.3}.get(plus, None)
        if v_supply is not None:
            v_drop = v_supply - V_base
            R_path = v_drop / (I_base / 1000.0)
            print(f"  Path drop: {v_drop:.4f} V   Estimated CH446Q Ron: {R_path:.1f} Ω")

    # ── Pass 2 ──────────────────────────────────────────────────────────────
    print(f"\n  Step 2 / 2 — With load")
    print(f"  Connect your load / circuit to {node!r} now.")
    input("  Press Enter when ready… ")

    m = _measure(conn, node, plus, sensor)
    if not m.get("ok"):
        print(f"  ERROR: {m.get('err', '?')}")
        return

    V_load = float(m["bus_v"])
    I_load = float(m.get("current_ma", 0.0))
    S_load = float(m.get("shunt_mv", 0.0))

    print(f"  Loaded  → V = {V_load:.4f} V   I = {I_load:.4f} mA   Shunt = {S_load:.4f} mV")

    # ── Results ─────────────────────────────────────────────────────────────
    I_net = I_load - I_base
    print(f"\n{sep}")
    print(f"  Results")
    print(sep)
    print(f"  Node voltage         : {V_load:>10.4f} V")
    if plus:
        print(f"  Total current        : {I_load:>10.4f} mA  (path + load)")
        print(f"  Baseline (path only) : {I_base:>10.4f} mA")
        print(f"  Net load current     : {I_net:>10.4f} mA  ← corrected")
        if I_net > 0:
            P_net = V_load * (I_net / 1000.0) * 1000.0
            print(f"  Load power           : {P_net:>10.4f} mW")
    print(sep + "\n")


def do_autodiff(conn, node: str, plus: str | None, sensor: int,
                samples: int = 30, interval: float = 0.15):
    """
    Auto-differential mode — collects samples, clusters them into two
    voltage states (HIGH / LOW), and reports each separately.
    Useful when measuring a node driven by a toggling signal (e.g. Nano PWM).
    """
    sep = "  " + "─" * 52

    print(f"\n  Auto-diff mode — {samples} samples at {interval}s interval")
    print(f"  Node: {node}    Plus: {plus or '(voltage only)'}    Sensor: {sensor}")
    print(f"  Keep the signal toggling freely…\n")
    print(f"  {'#':>5}  {'V (V)':>9}  {'I (mA)':>9}")
    print(f"  {'─'*30}")

    consecutive_errors = 0
    readings: list[dict] = []
    for i in range(samples):
        try:
            r = _measure(conn, node, plus, sensor)
        except Exception as e:
            consecutive_errors += 1
            print(f"  [{i+1:>3}]  error: {e}")
            if consecutive_errors >= 3:
                print("  3 consecutive timeouts — board not responding. Check connection.")
                break
            time.sleep(interval)
            continue

        if r.get("ok"):
            consecutive_errors = 0
            v = float(r["bus_v"])
            ci = float(r.get("current_ma", 0.0))
            readings.append({"v": v, "i": ci, "s": float(r.get("shunt_mv", 0.0))})
            print(f"  [{i+1:>3}]  {v:>9.4f}  {ci:>9.4f}")
        else:
            consecutive_errors += 1
            err = r.get("err", "?")
            print(f"  [{i+1:>3}]  error: {err}")
            if consecutive_errors >= 3:
                print(f"  Aborting — repeated error: '{err}'")
                break
        time.sleep(interval)

    if not readings:
        print("  No valid readings collected.")
        return

    # ── Cluster into two states ──────────────────────────────────────────────
    voltages = sorted(r["v"] for r in readings)
    v_mid = (voltages[0] + voltages[-1]) / 2.0

    lo = [r for r in readings if r["v"] <= v_mid]
    hi = [r for r in readings if r["v"] >  v_mid]

    def _avg(lst, key):
        return sum(x[key] for x in lst) / len(lst) if lst else 0.0

    print(f"\n{sep}")
    print(f"  Auto-diff results  ({len(readings)} samples, threshold = {v_mid:.4f} V)")
    print(sep)

    if lo and hi:
        print(f"  LOW  state  ({len(lo):>2} samples)")
        print(f"    V_avg = {_avg(lo,'v'):>9.4f} V   I_avg = {_avg(lo,'i'):>9.4f} mA")
        print(f"  HIGH state  ({len(hi):>2} samples)")
        print(f"    V_avg = {_avg(hi,'v'):>9.4f} V   I_avg = {_avg(hi,'i'):>9.4f} mA")
        dV = _avg(hi, "v") - _avg(lo, "v")
        dI = _avg(hi, "i") - _avg(lo, "i")
        print(f"  ΔV = {dV:+.4f} V   ΔI = {dI:+.4f} mA")
    else:
        # Signal is not toggling — single state
        state = lo if lo else hi
        print(f"  Single state  ({len(state)} samples — signal not toggling?)")
        print(f"    V_avg = {_avg(state,'v'):>9.4f} V   I_avg = {_avg(state,'i'):>9.4f} mA")

    print(sep + "\n")


def do_clear(conn):
    resp = _measure_clear(conn)
    if resp.get("ok"):
        print("  Netlist restored to full brightness.")
    else:
        print(f"  Clear failed: {resp}")


def interactive_mode(conn):
    print("JumperZ Measurement — Interactive Mode")
    print("  Commands:")
    print("    <node>                              voltage at node  (e.g.  TOP_17)")
    print("    <node> --node2 <node2>              differential: V(node2)−V(node)")
    print("    <node> --plus <src>                 current from src through node")
    print("    loop <node> [--node2 <n>|--plus <s>]  continuous until Ctrl+C")
    print("    diff <node> <node2>                 shorthand for differential")
    print("    guided <node> [--plus <src>]        two-pass: baseline then load")
    print("    autodiff <node> [--plus <src>]      auto-detect toggling signal")
    print("    clear                               restore netlist brightness")
    print("    q                                   quit (auto-restores)\n")

    while True:
        try:
            raw = input("measure> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue
        if raw.lower() in ("q", "quit", "exit"):
            break
        if raw.lower() == "clear":
            do_clear(conn)
            continue

        # simple tokenise: [loop|guided|autodiff|diff] <node> [--node2 <n>] [--plus <n>] [--sensor N]
        tokens = raw.split()
        verb = tokens[0].lower()
        continuous = verb == "loop"
        guided     = verb == "guided"
        autodiff   = verb == "autodiff"
        shortdiff  = verb == "diff"

        if continuous or guided or autodiff or shortdiff:
            tokens = tokens[1:]

        if not tokens:
            print("  usage: [loop|guided|autodiff|diff] <node> [--node2 <n>] [--plus <n>] [--sensor 0|1]")
            continue

        node   = tokens[0]
        plus   = None
        node2  = None
        sensor = 0
        i = 1

        # shorthand: diff <node> <node2>  (positional node2)
        if shortdiff and i < len(tokens) and not tokens[i].startswith("--"):
            node2 = tokens[i]; i += 1

        while i < len(tokens):
            if tokens[i] == "--node2" and i + 1 < len(tokens):
                node2 = tokens[i + 1]; i += 2
            elif tokens[i] == "--plus" and i + 1 < len(tokens):
                plus = tokens[i + 1]; i += 2
            elif tokens[i] == "--sensor" and i + 1 < len(tokens):
                try:   sensor = int(tokens[i + 1])
                except ValueError: pass
                i += 2
            else:
                i += 1

        try:
            if guided:
                do_guided(conn, node, plus, sensor)
            elif autodiff:
                do_autodiff(conn, node, plus, sensor)
            elif continuous or (shortdiff and not node2):
                do_continuous(conn, node, plus=plus, node2=node2, sensor=sensor)
            elif shortdiff or node2:
                _print_full(_measure(conn, node, node2=node2, sensor=sensor))
            else:
                _print_full(_measure(conn, node, plus=plus, sensor=sensor))
        except Exception as e:
            print(f"  [error] {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="JumperZ INA219 measurement  (voltage or current)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("node", nargs="?",
                        help="Node to measure (e.g. TOP_17, NANO_D3, BOTTOM_5)")
    parser.add_argument("--node2", default=None, metavar="NODE",
                        help="Second node → ISENSE+ for differential voltage (V(node2)−V(node))")
    parser.add_argument("--plus", default=None, metavar="NODE",
                        help="Supply node → ISENSE+ for current measurement")
    parser.add_argument("--sensor", type=int, default=0, choices=[0, 1],
                        help="INA219 index 0 or 1 (default: 0)")
    parser.add_argument("-c", "--continuous", action="store_true",
                        help="Measure continuously until Ctrl+C then restore")
    parser.add_argument("--interval", type=float, default=0.5,
                        help="Seconds between readings in continuous mode (default: 0.5)")
    parser.add_argument("--clear", action="store_true",
                        help="Restore netlist LED brightness and exit")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Interactive menu mode")
    parser.add_argument("--json", action="store_true",
                        help="Print raw JSON response (single measurement)")
    parser.add_argument("--guided", action="store_true",
                        help="Two-pass guided: baseline (no load) → connect load → corrected result")
    parser.add_argument("--autodiff", action="store_true",
                        help="Auto-detect toggling signal: cluster samples into HIGH/LOW states")
    parser.add_argument("--samples", type=int, default=30,
                        help="Number of samples for --autodiff (default: 30)")

    args = parser.parse_args()

    try:
        conn = BoardConn()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.clear:
            do_clear(conn)

        elif args.interactive:
            interactive_mode(conn)
            print("  Restoring netlist...")
            do_clear(conn)

        elif args.node:
            if args.guided:
                do_guided(conn, args.node, args.plus, args.sensor)
                print("  Restoring netlist...")
                do_clear(conn)
            elif args.autodiff:
                do_autodiff(conn, args.node, args.plus, args.sensor,
                            samples=args.samples, interval=args.interval)
                print("  Restoring netlist...")
                do_clear(conn)
            elif args.continuous:
                do_continuous(conn, args.node, plus=args.plus,
                              node2=args.node2, sensor=args.sensor,
                              interval=args.interval)
                print("  Restoring netlist...")
                do_clear(conn)
            else:
                ok = do_single(conn, args.node, plus=args.plus,
                               node2=args.node2, sensor=args.sensor,
                               as_json=args.json)
                if not ok:
                    sys.exit(1)

        else:
            parser.print_help()

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
