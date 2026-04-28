#!/usr/bin/env python3
"""
capacitance.py  —  Measure capacitor value via RC charging curve on JumperZ.

Method
------
1. Discharge cap to 0 V: firmware connects node_a → GND for discharge_ms.
2. At t=0 apply supply step through INA219 path.
3. Sample V(node_a) + I every interval_ms for `samples` points.
4. Fit voltage trace to:

       V(t) = Vcc × (1 − exp(−t / τ))    where τ = R_total × C

5. Extract  C = τ / R_total

Circuit during charging
-----------------------
    supply ─── ISENSE_PLUS ─── [INA219 shunt] ─── ISENSE_MINUS ─── node_a
                                                                         │
                                                                    [capacitor]
                                                                         │
                                                                    node_b ─── GND

R_total = R_internal (CH446Q Ron ≈ 200 Ω) + R_series (any external resistor).

Accuracy notes
--------------
- Works well for C ≥ ~100 nF  (τ ≥ 20 µs with R = 200 Ω).
- For C < 10 nF add a known external series resistor and pass --r-series.
- INA219 conversion ≈ 1 ms/reading → use --interval-ms ≥ 2.

Usage
-----
  python capacitance.py TOP_5 TOP_10
  python capacitance.py TOP_5 TOP_10 --supply 3V3 --samples 80 --plot
  python capacitance.py TOP_5 TOP_10 --r-series 10000 --interval-ms 20
"""

import sys
import argparse
import numpy as np
from scipy.optimize import curve_fit

sys.path.insert(0, "..")
from measure import BoardConn


DEFAULT_R_INTERNAL = 200.0


# ── RC model & fit ────────────────────────────────────────────────────────────

def _rc_charging(t, vcc, tau):
    return vcc * (1.0 - np.exp(-t / tau))


def _fit_rc(t_s, v, vcc_hint):
    """
    Fit V(t) = Vcc*(1-exp(-t/tau)).  Returns (vcc_fit, tau_s, r2).
    Falls back to 63.2 % threshold crossing if scipy fails.
    """
    tau_guess = float(t_s[-1]) / 3.0
    try:
        popt, _ = curve_fit(
            _rc_charging, t_s, v,
            p0=[vcc_hint, tau_guess],
            bounds=([0.0, 1e-9], [30.0, 60.0]),
            maxfev=8000,
        )
        vcc_fit, tau_fit = float(popt[0]), float(popt[1])
    except RuntimeError:
        idx = int(np.searchsorted(v, vcc_hint * 0.632))
        tau_fit = float(t_s[min(idx, len(t_s) - 1)])
        vcc_fit = vcc_hint

    v_pred = _rc_charging(t_s, vcc_fit, tau_fit)
    ss_res = float(np.sum((v - v_pred) ** 2))
    ss_tot = float(np.sum((v - np.mean(v)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return vcc_fit, tau_fit, r2


# ── public API ────────────────────────────────────────────────────────────────

def measure_capacitance(node_a, node_b, supply="3V3",
                         r_internal=DEFAULT_R_INTERNAL,
                         r_series=0.0,
                         samples=60, interval_ms=5,
                         discharge_ms=400,
                         sensor=0) -> dict:
    """
    Measure capacitance between node_a (high plate) and node_b (GND plate).

    Returns dict:
        capacitance_uf, tau_ms, r_total_ohm, vcc_fit, fit_quality,
        samples (raw list), supply, node_a, node_b
    """
    r_total = r_internal + r_series

    with BoardConn() as conn:
        resp = conn.send({
            "cmd":          "measure_sweep",
            "node":         node_a,
            "plus":         supply,
            "ref":          node_b,
            "samples":      samples,
            "interval_ms":  interval_ms,
            "discharge_ms": discharge_ms,
            "sensor":       sensor,
        })
        if not resp.get("ok"):
            raise RuntimeError(f"measure_sweep failed: {resp}")
        raw = resp["samples"]
        conn.send({"cmd": "measure_clear"})

    t_s = np.array([s["t_ms"] / 1000.0 for s in raw])
    v   = np.array([s["v"]             for s in raw])

    vcc_hint = float(v[-1]) if float(v[-1]) > 0.1 else (3.3 if "3" in supply else 5.0)
    vcc_fit, tau_fit, r2 = _fit_rc(t_s, v, vcc_hint)

    c_uf = (tau_fit / r_total) * 1e6

    return {
        "capacitance_uf": round(c_uf,    6),
        "tau_ms":         round(tau_fit * 1000, 4),
        "r_total_ohm":    r_total,
        "r_internal_ohm": r_internal,
        "r_series_ohm":   r_series,
        "vcc_fit":        round(vcc_fit,  4),
        "fit_quality":    round(r2,       5),
        "samples":        raw,
        "supply":         supply,
        "node_a":         node_a,
        "node_b":         node_b,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli():
    p = argparse.ArgumentParser(description="JumperZ capacitance measurement")
    p.add_argument("node_a",  help="High-plate node, e.g. TOP_5")
    p.add_argument("node_b",  help="GND-plate node,  e.g. TOP_10")
    p.add_argument("--supply",        default="3V3")
    p.add_argument("--r-internal",    type=float, default=DEFAULT_R_INTERNAL,
                   help=f"CH446Q path resistance Ω (default: {DEFAULT_R_INTERNAL})")
    p.add_argument("--r-series",      type=float, default=0.0,
                   help="External series resistor Ω (default: 0)")
    p.add_argument("--samples",       type=int,   default=60)
    p.add_argument("--interval-ms",   type=int,   default=5)
    p.add_argument("--discharge-ms",  type=int,   default=400)
    p.add_argument("--sensor",        type=int,   default=0)
    p.add_argument("--plot",          action="store_true",
                   help="Show RC charging curve plot")
    p.add_argument("--save",          default=None,
                   help="Save plot to file instead of displaying")
    args = p.parse_args()

    result = measure_capacitance(
        args.node_a, args.node_b,
        supply=args.supply,
        r_internal=args.r_internal,
        r_series=args.r_series,
        samples=args.samples,
        interval_ms=args.interval_ms,
        discharge_ms=args.discharge_ms,
        sensor=args.sensor,
    )

    sep = "=" * 46
    print(f"\n{sep}")
    print(f"  Capacitance  :  {result['capacitance_uf']:.4f} µF")
    print(f"  Time const   :  {result['tau_ms']:.3f} ms")
    print(f"  R total      :  {result['r_total_ohm']:.1f} Ω")
    print(f"  Vcc fitted   :  {result['vcc_fit']:.4f} V")
    print(f"  Fit quality  :  {result['fit_quality']:.5f}  (R²)")
    print(sep)

    if args.plot or args.save:
        from vi_graph import plot_vi_capacitor
        plot_vi_capacitor(
            result["samples"],
            r_total=result["r_total_ohm"],
            node_a=args.node_a, node_b=args.node_b,
            supply=args.supply,
            c_uf=result["capacitance_uf"],
            tau_ms=result["tau_ms"],
            save_path=args.save,
        )


if __name__ == "__main__":
    _cli()
