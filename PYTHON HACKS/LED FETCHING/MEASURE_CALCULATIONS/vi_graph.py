#!/usr/bin/env python3
"""
vi_graph.py  —  V-I characteristic plots for JumperZ component measurements.

Two plot functions:

  plot_vi_resistor(samples, ...)
      Left  — V-I scatter with linear best-fit line and R annotation.
      Right — V(t) and I(t) time traces on a dual-axis chart.

  plot_vi_capacitor(samples, ...)
      Left   — V(t) charging curve with RC exponential fit overlay.
      Centre — I(t) decay curve.
      Right  — V-I lissajous coloured by time (reveals capacitive character).

Can also be run as a standalone CLI:

  python vi_graph.py TOP_5 TOP_10 --mode resistor --plot
  python vi_graph.py TOP_5 TOP_10 --mode capacitor --plot --discharge-ms 400
  python vi_graph.py TOP_5 TOP_10 --mode resistor --save graph.png
"""

import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

sys.path.insert(0, "..")


# ── Resistor V-I graph ────────────────────────────────────────────────────────

def plot_vi_resistor(samples: list, r_internal: float = 200.0,
                      node_a: str = "node_a", node_b: str = "node_b",
                      supply: str = "5V", save_path: str = None) -> float:
    """
    Plot V-I characteristic for a resistor sweep.

    Parameters
    ----------
    samples     : list of {"t_ms", "v" [V], "i" [mA]} from resistance.vi_sweep()
    r_internal  : CH446Q path resistance to subtract
    save_path   : if given, save figure to this path; else plt.show()

    Returns
    -------
    r_component_ohm : best-fit component resistance
    """
    t  = np.array([s["t_ms"] for s in samples], dtype=float)
    v  = np.array([s["v"]    for s in samples], dtype=float)
    i  = np.array([s["i"]    for s in samples], dtype=float) / 1000.0  # → A

    valid = i > 1e-6
    if not np.any(valid):
        print("No valid current readings — check connections and component.")
        return 0.0

    v_v, i_v = v[valid], i[valid]

    # Linear V-I fit forced through origin: slope = R_total
    r_total_fit = float(np.dot(v_v, i_v) / np.dot(i_v, i_v))
    r_comp = max(0.0, r_total_fit - r_internal)

    fig = plt.figure(figsize=(13, 5))
    gs  = GridSpec(1, 2, figure=fig, wspace=0.38)

    # ── Left: V-I scatter + fit ───────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])

    ax1.scatter(i_v * 1000, v_v, color="royalblue", s=35, zorder=3,
                label="Measured points")

    i_line = np.linspace(0, i_v.max() * 1.08, 300)
    ax1.plot(i_line * 1000, i_line * r_total_fit,
             color="tomato", lw=2.0,
             label=f"Linear fit  R_total = {r_total_fit:.1f} Ω")

    ax1.set_xlabel("Current (mA)")
    ax1.set_ylabel("Voltage (V)")
    ax1.set_title(f"V-I Characteristic\n{node_a} → {node_b}  |  supply: {supply}")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    info = (f"R_total   = {r_total_fit:.1f} Ω\n"
            f"R_path    = {r_internal:.1f} Ω\n"
            f"R_comp  ≈ {r_comp:.1f} Ω")
    ax1.text(0.97, 0.05, info, transform=ax1.transAxes,
             va="bottom", ha="right", fontsize=9,
             bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.75))

    # ── Right: V(t) and I(t) time traces ──────────────────────────────────────
    ax2   = fig.add_subplot(gs[1])
    ax2r  = ax2.twinx()

    l1, = ax2.plot(t, v, color="royalblue", lw=1.8, label="V (V)")
    l2, = ax2r.plot(t, i * 1000, color="tomato", lw=1.8,
                    linestyle="--", label="I (mA)")

    ax2.set_xlabel("Time (ms)")
    ax2.set_ylabel("Voltage (V)", color="royalblue")
    ax2r.set_ylabel("Current (mA)", color="tomato")
    ax2.set_title("Time Traces")
    ax2.legend(handles=[l1, l2], loc="upper right", fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.suptitle(f"Resistance Measurement — {node_a} to {node_b}",
                 fontsize=11, y=1.01)
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved → {save_path}")
    else:
        plt.show()

    return r_comp


# ── Capacitor V-I graph ───────────────────────────────────────────────────────

def plot_vi_capacitor(samples: list, r_total: float = 200.0,
                       node_a: str = "node_a", node_b: str = "node_b",
                       supply: str = "3V3",
                       c_uf: float = None, tau_ms: float = None,
                       save_path: str = None) -> float:
    """
    Plot RC charging curve with exponential fit + current decay + V-I lissajous.

    Parameters
    ----------
    samples  : list of {"t_ms", "v" [V], "i" [mA]} from capacitance.measure_capacitance()
    r_total  : R_internal + R_series used for the C calculation
    c_uf     : if already known (from capacitance.py), shown in annotation
    tau_ms   : if already known, shown in annotation
    save_path: save figure to path if given; else plt.show()

    Returns
    -------
    c_uf_fit : capacitance from fit in µF
    """
    from scipy.optimize import curve_fit

    t_ms = np.array([s["t_ms"] for s in samples], dtype=float)
    v    = np.array([s["v"]    for s in samples], dtype=float)
    i    = np.array([s["i"]    for s in samples], dtype=float)   # mA
    t_s  = t_ms / 1000.0

    def _rc(t, vcc, tau):
        return vcc * (1.0 - np.exp(-t / tau))

    vcc_hint  = float(v[-1]) if float(v[-1]) > 0.1 else (3.3 if "3" in supply else 5.0)
    tau_guess = float(t_s[-1]) / 3.0
    try:
        popt, _ = curve_fit(_rc, t_s, v, p0=[vcc_hint, tau_guess],
                             bounds=([0, 1e-9], [30, 60]), maxfev=8000)
        vcc_fit, tau_fit = float(popt[0]), float(popt[1])
    except RuntimeError:
        tau_fit  = tau_guess
        vcc_fit  = vcc_hint

    c_fit_uf = (tau_fit / r_total) * 1e6

    fig = plt.figure(figsize=(15, 5))
    gs  = GridSpec(1, 3, figure=fig, wspace=0.42)

    # ── Left: V(t) + RC fit ───────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])

    ax1.scatter(t_ms, v, color="royalblue", s=20, zorder=3, label="Measured V")

    t_fit_ms = np.linspace(0, t_ms[-1], 600)
    ax1.plot(t_fit_ms, _rc(t_fit_ms / 1000.0, vcc_fit, tau_fit),
             color="tomato", lw=2.0,
             label=f"RC fit  τ = {tau_fit*1000:.2f} ms")

    # Mark τ crossing
    ax1.axvline(tau_fit * 1000, color="gray", lw=1.2, ls="--", alpha=0.6)
    ax1.axhline(vcc_fit * 0.632, color="gray", lw=1.2, ls="--", alpha=0.6)
    ax1.text(tau_fit * 1000 * 1.02, vcc_fit * 0.632 * 1.02,
             "63.2%", fontsize=8, color="gray")

    ax1.set_xlabel("Time (ms)")
    ax1.set_ylabel("Voltage (V)")
    ax1.set_title(f"RC Charging Curve\n{node_a} → {node_b}")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    disp_c   = c_uf if c_uf is not None else c_fit_uf
    disp_tau = tau_ms if tau_ms is not None else tau_fit * 1000
    info = (f"C  ≈ {disp_c:.4f} µF\n"
            f"τ  = {disp_tau:.3f} ms\n"
            f"Vcc= {vcc_fit:.3f} V\n"
            f"R  = {r_total:.1f} Ω")
    ax1.text(0.97, 0.05, info, transform=ax1.transAxes,
             va="bottom", ha="right", fontsize=9,
             bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.75))

    # ── Centre: I(t) decay ────────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(t_ms, i, color="darkorange", lw=1.8)
    ax2.set_xlabel("Time (ms)")
    ax2.set_ylabel("Current (mA)")
    ax2.set_title("Current Decay")
    ax2.grid(True, alpha=0.3)

    # ── Right: V-I lissajous (colour = time) ──────────────────────────────────
    ax3 = fig.add_subplot(gs[2])
    sc  = ax3.scatter(i, v, c=t_ms, cmap="plasma", s=25, zorder=3)
    cbar = plt.colorbar(sc, ax=ax3, pad=0.02)
    cbar.set_label("Time (ms)", fontsize=9)
    ax3.set_xlabel("Current (mA)")
    ax3.set_ylabel("Voltage (V)")
    ax3.set_title("V-I  (colour = time)")
    ax3.grid(True, alpha=0.3)

    plt.suptitle(
        f"Capacitance Measurement — {node_a} to {node_b}  |  supply: {supply}",
        fontsize=11, y=1.01,
    )
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved → {save_path}")
    else:
        plt.show()

    return c_fit_uf


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli():
    p = argparse.ArgumentParser(description="JumperZ V-I characteristic plotter")
    p.add_argument("node_a")
    p.add_argument("node_b")
    p.add_argument("--mode",         choices=["resistor", "capacitor"],
                   default="resistor")
    p.add_argument("--supply",       default="5V")
    p.add_argument("--r-internal",   type=float, default=200.0)
    p.add_argument("--r-series",     type=float, default=0.0)
    p.add_argument("--samples",      type=int,   default=40)
    p.add_argument("--interval-ms",  type=int,   default=8)
    p.add_argument("--discharge-ms", type=int,   default=0)
    p.add_argument("--sensor",       type=int,   default=0)
    p.add_argument("--save",         default=None)
    p.add_argument("--plot",         action="store_true",
                   help="Show the plot window (default when --save is not given)")
    args = p.parse_args()

    if args.mode == "capacitor":
        from capacitance import measure_capacitance
        result = measure_capacitance(
            args.node_a, args.node_b,
            supply=args.supply,
            r_internal=args.r_internal,
            r_series=args.r_series,
            samples=args.samples,
            interval_ms=args.interval_ms,
            discharge_ms=args.discharge_ms if args.discharge_ms > 0 else 400,
            sensor=args.sensor,
        )
        plot_vi_capacitor(
            result["samples"],
            r_total=result["r_total_ohm"],
            node_a=args.node_a, node_b=args.node_b,
            supply=args.supply,
            c_uf=result["capacitance_uf"],
            tau_ms=result["tau_ms"],
            save_path=args.save,
        )
    else:
        from resistance import vi_sweep
        data = vi_sweep(
            args.node_a, args.node_b,
            supply=args.supply,
            samples=args.samples,
            interval_ms=args.interval_ms,
            sensor=args.sensor,
        )
        plot_vi_resistor(
            data,
            r_internal=args.r_internal,
            node_a=args.node_a, node_b=args.node_b,
            supply=args.supply,
            save_path=args.save,
        )


if __name__ == "__main__":
    _cli()
