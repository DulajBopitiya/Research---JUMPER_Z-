#!/usr/bin/env python3
"""
resistance.py  —  Measure resistor value via JumperZ INA219.

Principle
---------
The INA219 is placed in-series with the measurement path:

    supply ─── ISENSE_PLUS ─── [INA219 shunt] ─── ISENSE_MINUS ─── node_a
                                                                         │
                                                                    [R_component]
                                                                         │
                                                                    node_b ─── GND

    R_total     = V(node_a) / I
    R_component = R_total − R_path_internal

R_path_internal is the sum of CH446Q switch Ron values in the path.
Default estimate: ~200 Ω.  Run --calibrate with a short to measure it precisely.

Usage
-----
  python resistance.py TOP_5 TOP_10
  python resistance.py TOP_5 TOP_10 --supply 5V --r-internal 220
  python resistance.py TOP_5 TOP_10 --calibrate        (short the nodes first)
  python resistance.py TOP_5 TOP_10 --sweep --plot      V-I graph
"""

import sys
import argparse
import numpy as np

sys.path.insert(0, "..")   # allow running from this sub-folder
from measure import BoardConn


DEFAULT_R_INTERNAL = 200.0   # ohms — estimated CH446Q path resistance


# ── helpers ───────────────────────────────────────────────────────────────────

def _averaged_measure(conn, node_a, node_b, supply, sensor, n_avg):
    """
    Take n_avg single INA219 readings and return (v_volts, i_ma, r_total_ohm).
    node_b must already be routed to GND before calling.
    """
    vs, is_ = [], []
    for _ in range(n_avg):
        r = conn.send({"cmd": "measure", "node": node_a,
                       "plus": supply, "sensor": sensor})
        if not r.get("ok"):
            raise RuntimeError(f"measure failed: {r}")
        vs.append(r["bus_v"])
        is_.append(r["current_ma"])

    v_avg = float(np.mean(vs))
    i_avg = float(np.mean(is_))
    r_total = (v_avg / (i_avg / 1000.0)) if i_avg > 0.05 else float("inf")
    return v_avg, i_avg, r_total


# ── public API ────────────────────────────────────────────────────────────────

def measure_resistance(node_a, node_b, supply="5V",
                       r_internal=DEFAULT_R_INTERNAL,
                       n_avg=8, sensor=0) -> dict:
    """
    Measure resistance of component between node_a and node_b.

    Returns dict:
        r_component_ohm, r_total_ohm, r_internal_ohm,
        v_volts, i_ma, supply, node_a, node_b
    """
    with BoardConn() as conn:
        ack = conn.send({"cmd": "connect",
                         "nets": [{"nodes": [node_b, "GND"], "color": "#555555"}]})
        if not ack.get("ok"):
            raise RuntimeError(f"connect failed: {ack}")

        v, i, r_total = _averaged_measure(conn, node_a, node_b,
                                           supply, sensor, n_avg)
        conn.send({"cmd": "measure_clear"})

    r_comp = max(0.0, r_total - r_internal)
    return {
        "r_component_ohm": round(r_comp,  1),
        "r_total_ohm":     round(r_total, 1),
        "r_internal_ohm":  r_internal,
        "v_volts":         round(v, 4),
        "i_ma":            round(i, 3),
        "supply":          supply,
        "node_a":          node_a,
        "node_b":          node_b,
    }


def calibrate_internal(node_a, node_b, supply="5V", sensor=0) -> float:
    """
    Measure R_internal with node_a and node_b shorted by a wire.
    Returns the R_internal value to use in subsequent calls.
    """
    with BoardConn() as conn:
        ack = conn.send({"cmd": "connect",
                         "nets": [{"nodes": [node_b, "GND"], "color": "#555555"}]})
        if not ack.get("ok"):
            raise RuntimeError(f"connect failed: {ack}")

        v, i, r_int = _averaged_measure(conn, node_a, node_b,
                                         supply, sensor, n_avg=16)
        conn.send({"cmd": "measure_clear"})

    print(f"R_internal = {r_int:.1f} Ω   (V={v:.4f} V,  I={i:.3f} mA)")
    return r_int


def vi_sweep(node_a, node_b, supply="5V",
              samples=40, interval_ms=8, sensor=0) -> list:
    """
    Take a multi-sample V-I sweep using measure_sweep firmware command.
    Returns list of {"t_ms": int, "v": float [V], "i": float [mA]}.
    Suitable for plot_vi_resistor() in vi_graph.py.
    """
    with BoardConn() as conn:
        resp = conn.send({
            "cmd":         "measure_sweep",
            "node":        node_a,
            "plus":        supply,
            "ref":         node_b,
            "samples":     samples,
            "interval_ms": interval_ms,
            "sensor":      sensor,
        })
        if not resp.get("ok"):
            raise RuntimeError(f"measure_sweep failed: {resp}")
        raw = resp["samples"]
        conn.send({"cmd": "measure_clear"})

    return raw


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli():
    p = argparse.ArgumentParser(description="JumperZ resistance measurement")
    p.add_argument("node_a",  help="High-side node, e.g. TOP_5")
    p.add_argument("node_b",  help="Low-side node,  e.g. TOP_10")
    p.add_argument("--supply",      default="5V",
                   help="Supply node (default: 5V)")
    p.add_argument("--r-internal",  type=float, default=DEFAULT_R_INTERNAL,
                   help=f"Path resistance to subtract in Ω (default: {DEFAULT_R_INTERNAL})")
    p.add_argument("--n-avg",       type=int,   default=8,
                   help="Readings to average for simple mode (default: 8)")
    p.add_argument("--sensor",      type=int,   default=0)
    p.add_argument("--calibrate",   action="store_true",
                   help="Calibration mode: short node_a↔node_b first, then run")
    p.add_argument("--sweep",       action="store_true",
                   help="Use multi-sample V-I sweep instead of averaged single-shot")
    p.add_argument("--samples",     type=int,   default=40)
    p.add_argument("--interval-ms", type=int,   default=8)
    p.add_argument("--plot",        action="store_true",
                   help="Show V-I graph after sweep (requires --sweep)")
    p.add_argument("--save",        default=None,
                   help="Save plot to file instead of displaying")
    args = p.parse_args()

    sep = "=" * 46

    if args.calibrate:
        r_int = calibrate_internal(args.node_a, args.node_b,
                                    supply=args.supply, sensor=args.sensor)
        print(f"\nUse  --r-internal {r_int:.1f}  for future measurements.")

    elif args.sweep:
        data = vi_sweep(args.node_a, args.node_b,
                        supply=args.supply,
                        samples=args.samples,
                        interval_ms=args.interval_ms,
                        sensor=args.sensor)
        # Quick R estimate from mean V/I
        vs = np.array([s["v"] for s in data])
        is_ = np.array([s["i"] / 1000.0 for s in data])
        valid = is_ > 1e-6
        if np.any(valid):
            r_fit = float(np.dot(vs[valid], is_[valid]) / np.dot(is_[valid], is_[valid]))
            r_comp = max(0.0, r_fit - args.r_internal)
            print(f"\n{sep}")
            print(f"  R (V-I fit)  :  {r_comp:.1f} Ω  (R_total={r_fit:.1f}, R_int={args.r_internal:.1f})")
            print(sep)

        if args.plot or args.save:
            from vi_graph import plot_vi_resistor
            plot_vi_resistor(data,
                             r_internal=args.r_internal,
                             node_a=args.node_a, node_b=args.node_b,
                             supply=args.supply, save_path=args.save)

    else:
        result = measure_resistance(
            args.node_a, args.node_b,
            supply=args.supply,
            r_internal=args.r_internal,
            n_avg=args.n_avg,
            sensor=args.sensor,
        )
        print(f"\n{sep}")
        print(f"  Measured R   :  {result['r_component_ohm']:.1f} Ω")
        print(f"  R_total      :  {result['r_total_ohm']:.1f} Ω")
        print(f"  R_internal   :  {result['r_internal_ohm']:.1f} Ω  (subtracted)")
        print(f"  V @ node_a   :  {result['v_volts']:.4f} V")
        print(f"  Current      :  {result['i_ma']:.3f} mA")
        print(f"  Supply       :  {result['supply']}")
        print(sep)


if __name__ == "__main__":
    _cli()
