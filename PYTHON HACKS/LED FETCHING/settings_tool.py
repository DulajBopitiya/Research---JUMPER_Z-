#!/usr/bin/env python3
"""
settings_tool.py — JumperZ persistent settings manager.

Reads and writes board settings that survive power-cycles (stored in the
RP2040 on-chip flash via EEPROM emulation).

Supported settings
------------------
  brightness         LED strip global brightness  0–255   (default 50)
  conn_anim          USB-connect animation        bool    (default false)
  disconn_anim       USB-disconnect animation     bool    (default false)
  osc_conn_style     Oscilloscope plug-in animation       (default 1=scopewave)
                       0=off  1=scopewave  2=comet  3=ripple  4=matrixrain
  osc_disconn_style  Oscilloscope unplug animation        (default 1=flatline)
                       0=off  1=flatline  2=redfade  3=drain

Usage
-----
  python settings_tool.py                        interactive menu
  python settings_tool.py --get                  print current settings + eeprom status
  python settings_tool.py --set brightness=80
  python settings_tool.py --set brightness=80 conn_anim=true disconn_anim=false
  python settings_tool.py --set osc_conn_style=ripple
  python settings_tool.py --set osc_conn_style=0 osc_disconn_style=drain
  python settings_tool.py --verify               check EEPROM matches RAM (debug)
  python settings_tool.py --reset                restore factory defaults
"""

import argparse
import json
import sys
import time

import serial
import serial.tools.list_ports

# ---------------------------------------------------------------------------
# Port detection (mirrors bridge_send.py logic)
# ---------------------------------------------------------------------------

VID_TOKEN = "1D51"
PID_TOKEN = "ACAB"
BRIDGE_LOC_SUFFIX = "X.2"   # JZ NETSH = CDC index 1


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


# ---------------------------------------------------------------------------
# Board connection
# ---------------------------------------------------------------------------

class BoardConn:
    def __init__(self, baud: int = 115200, timeout: float = 3.0):
        port = find_bridge_port()
        if not port:
            raise RuntimeError(
                "JumperZ bridge port (JZ NETSH) not found.\n"
                "Is the board plugged in and USB cable data-capable?"
            )
        self._port_name = port
        self._s = serial.Serial(port, baudrate=baud, timeout=timeout, write_timeout=2)
        time.sleep(0.15)  # Windows CDC settle

    def send(self, payload: dict) -> dict:
        line = json.dumps(payload, separators=(",", ":")) + "\n"
        self._s.write(line.encode("utf-8"))
        raw = self._s.readline()
        if not raw:
            raise TimeoutError("No response from board (timeout).")
        return json.loads(raw.decode("utf-8").strip())

    def close(self):
        self._s.close()

    @property
    def port(self) -> str:
        return self._port_name


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

SETTING_KEYS = (
    "brightness", "conn_anim", "disconn_anim",
    "osc_conn_style", "osc_disconn_style",
)

SETTING_DESCRIPTIONS = {
    "brightness":        "LED strip brightness  (0–255, default 50)",
    "conn_anim":         "Play animation on USB connect     (true/false, default false)",
    "disconn_anim":      "Play animation on USB disconnect  (true/false, default false)",
    "osc_conn_style":    "OSC plug-in animation  (0=off, 1=scopewave, 2=comet, 3=ripple, 4=matrixrain)",
    "osc_disconn_style": "OSC unplug animation   (0=off, 1=flatline, 2=redfade, 3=drain)",
}

# Style index → friendly name
OSC_CONN_STYLES = {
    0: "off",
    1: "scopewave",
    2: "comet",
    3: "ripple",
    4: "matrixrain",
}
OSC_DISCONN_STYLES = {
    0: "off",
    1: "flatline",
    2: "redfade",
    3: "drain",
}
# Reverse lookup (name → index) for accepting names from the user
OSC_CONN_NAMES    = {v: k for k, v in OSC_CONN_STYLES.items()}
OSC_DISCONN_NAMES = {v: k for k, v in OSC_DISCONN_STYLES.items()}


def _style_label(table: dict[int, str], idx) -> str:
    """Render `2` as 'comet (2)' for display."""
    try:
        i = int(idx)
    except (TypeError, ValueError):
        return f"? ({idx})"
    return f"{table.get(i, 'unknown')} ({i})"


def _coerce(key: str, raw: str):
    """Parse a user-supplied string into the correct Python type for `key`.
    Accepts both numeric and friendly-name forms for the OSC style fields."""
    if key == "brightness":
        v = int(raw)
        if not 0 <= v <= 255:
            raise ValueError("brightness must be 0–255")
        return v
    if key in ("conn_anim", "disconn_anim"):
        if raw.lower() in ("true", "1", "yes", "on"):
            return True
        if raw.lower() in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"{key} must be true or false")
    if key == "osc_conn_style":
        return _coerce_style(raw, OSC_CONN_STYLES, OSC_CONN_NAMES, key)
    if key == "osc_disconn_style":
        return _coerce_style(raw, OSC_DISCONN_STYLES, OSC_DISCONN_NAMES, key)
    raise ValueError(f"Unknown setting key: {key!r}")


def _coerce_style(raw: str, idx_table: dict[int, str],
                  name_table: dict[str, int], key: str) -> int:
    s = raw.strip().lower()
    if s.isdigit():
        n = int(s)
        if n in idx_table:
            return n
        raise ValueError(
            f"{key} index {n} out of range; valid: {sorted(idx_table)}"
        )
    if s in name_table:
        return name_table[s]
    valid = ", ".join(f"{i}={n}" for i, n in idx_table.items())
    raise ValueError(f"{key} must be one of: {valid}")


def _fmt(cfg: dict, eeprom_ok: bool | None = None, save_ok: bool | None = None) -> str:
    lines = []
    for k in SETTING_KEYS:
        v = cfg.get(k, "?")
        # Render style fields with their friendly name in parentheses
        if k == "osc_conn_style":
            v_str = _style_label(OSC_CONN_STYLES, v)
        elif k == "osc_disconn_style":
            v_str = _style_label(OSC_DISCONN_STYLES, v)
        else:
            v_str = str(v)
        desc = SETTING_DESCRIPTIONS.get(k, "")
        lines.append(f"  {k:<18} = {v_str:<18}  # {desc}")
    if eeprom_ok is not None:
        status = "OK" if eeprom_ok else "FAIL - EEPROM not responding!"
        lines.append(f"\n  eeprom_ok          = {status}")
    if save_ok is not None:
        status = "OK" if save_ok else "FAIL - write did not ACK (settings NOT saved!)"
        lines.append(f"  save_ok            = {status}")
    return "\n".join(lines)


def get_settings(conn: BoardConn) -> dict:
    resp = conn.send({"cmd": "settings", "action": "get"})
    if not resp.get("ok"):
        raise RuntimeError(f"Board error: {resp}")
    return resp   # return full response so callers can inspect eeprom_ok etc.


def set_settings(conn: BoardConn, updates: dict) -> dict:
    payload = {"cmd": "settings", "action": "set"}
    payload.update(updates)
    resp = conn.send(payload)
    if not resp.get("ok"):
        raise RuntimeError(f"Board error: {resp}")
    return resp


def reset_settings(conn: BoardConn) -> dict:
    resp = conn.send({"cmd": "settings", "action": "reset"})
    if not resp.get("ok"):
        raise RuntimeError(f"Board error: {resp}")
    return resp


def verify_settings(conn: BoardConn) -> dict:
    resp = conn.send({"cmd": "settings", "action": "verify"})
    if not resp.get("ok"):
        raise RuntimeError(f"Board error: {resp}")
    return resp


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

def interactive_menu(conn: BoardConn):
    print(f"\nConnected to JumperZ on {conn.port}")

    while True:
        resp = get_settings(conn)
        eeprom_ok = resp.get("eeprom_ok")

        print("\n╔══════════════════════════════════════════╗")
        print("║        JumperZ Settings Manager          ║")
        print("╚══════════════════════════════════════════╝")
        print("\nCurrent settings:")
        print(_fmt(resp, eeprom_ok=eeprom_ok))
        if eeprom_ok is False:
            print("\n  *** WARNING: EEPROM not responding — changes will NOT survive reboot ***")
        print()
        print("  [1] Change brightness")
        print("  [2] Toggle conn_anim         (USB connect animation)")
        print("  [3] Toggle disconn_anim      (USB disconnect animation)")
        print("  [4] Pick OSC connect style   (oscilloscope plug-in animation)")
        print("  [5] Pick OSC disconnect style (oscilloscope unplug animation)")
        print("  [v] Verify EEPROM contents match RAM")
        print("  [r] Reset to factory defaults")
        print("  [q] Quit")
        print()

        choice = input("Choice: ").strip().lower()

        if choice == "q":
            print("Bye.")
            break

        elif choice == "v":
            vresp = verify_settings(conn)
            match = vresp.get("match", False)
            eok   = vresp.get("eeprom_ok", False)
            if not eok:
                print("EEPROM not responding — check I2C wiring (SDA=GPIO4, SCL=GPIO5, addr=0x50)")
            elif match:
                print("EEPROM matches RAM — settings are persisted correctly.")
            else:
                print("EEPROM does NOT match RAM — last save failed!")

        elif choice == "r":
            confirm = input("Reset ALL settings to factory defaults? (yes/no): ").strip().lower()
            if confirm == "yes":
                rresp = reset_settings(conn)
                save_ok = rresp.get("save_ok")
                print("Factory defaults restored." if save_ok else "Reset command sent but EEPROM write FAILED.")
                print(_fmt(rresp, eeprom_ok=rresp.get("eeprom_ok"), save_ok=save_ok))
            else:
                print("Cancelled.")

        elif choice == "1":
            raw = input(f"New brightness (0–255) [{resp.get('brightness', '?')}]: ").strip()
            if not raw:
                print("Unchanged.")
                continue
            try:
                v = _coerce("brightness", raw)
            except ValueError as e:
                print(f"Invalid value: {e}")
                continue
            sresp = set_settings(conn, {"brightness": v})
            save_ok = sresp.get("save_ok")
            if save_ok is False:
                print(f"brightness set to {sresp.get('brightness')} in RAM, but EEPROM write FAILED — will not survive reboot!")
            else:
                print(f"brightness set to {sresp.get('brightness')}  (applied immediately, saved to EEPROM)")

        elif choice == "2":
            new_val = not resp.get("conn_anim", False)
            sresp = set_settings(conn, {"conn_anim": new_val})
            save_ok = sresp.get("save_ok")
            msg = "saved" if save_ok else "NOT saved (EEPROM write failed)"
            print(f"conn_anim set to {sresp.get('conn_anim')} — {msg}")

        elif choice == "3":
            new_val = not resp.get("disconn_anim", False)
            sresp = set_settings(conn, {"disconn_anim": new_val})
            save_ok = sresp.get("save_ok")
            msg = "saved" if save_ok else "NOT saved (EEPROM write failed)"
            print(f"disconn_anim set to {sresp.get('disconn_anim')} — {msg}")

        elif choice == "4":
            _pick_style(conn, "osc_conn_style", OSC_CONN_STYLES,
                        resp.get("osc_conn_style"))

        elif choice == "5":
            _pick_style(conn, "osc_disconn_style", OSC_DISCONN_STYLES,
                        resp.get("osc_disconn_style"))

        else:
            print("Unknown option — try again.")


def _pick_style(conn: BoardConn, key: str,
                styles: dict[int, str], current) -> None:
    """Show numbered list, prompt user, send the chosen style to the board."""
    print(f"\nCurrent {key}: {_style_label(styles, current)}")
    print("Available styles:")
    for idx, name in styles.items():
        marker = " *" if current == idx else "  "
        print(f"   {marker} [{idx}] {name}")
    raw = input("Pick a style (number or name, blank to cancel): ").strip()
    if not raw:
        print("Unchanged.")
        return
    try:
        v = _coerce(key, raw)
    except ValueError as e:
        print(f"Invalid value: {e}")
        return
    sresp = set_settings(conn, {key: v})
    save_ok = sresp.get("save_ok")
    label   = _style_label(styles, sresp.get(key))
    msg     = "saved to EEPROM" if save_ok else "NOT saved (EEPROM write failed)"
    print(f"{key} → {label} — {msg}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="JumperZ persistent settings manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--get",    action="store_true", help="Print current settings and EEPROM status")
    ap.add_argument("--set",    nargs="+", metavar="KEY=VALUE",
                    help="Set one or more settings (e.g. brightness=80 conn_anim=true)")
    ap.add_argument("--verify", action="store_true", help="Check EEPROM matches RAM (debug)")
    ap.add_argument("--reset",  action="store_true", help="Restore factory defaults")
    args = ap.parse_args()

    try:
        conn = BoardConn()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.verify:
            vresp = verify_settings(conn)
            match    = vresp.get("match", False)
            eeprom_ok = vresp.get("eeprom_ok", False)
            print(json.dumps(vresp, indent=2))
            if not eeprom_ok:
                print("\nEEPROM not responding — check wiring (SDA=GPIO4, SCL=GPIO5) and I2C address (0x50).")
                sys.exit(1)
            elif not match:
                print("\nMismatch — last save did not write correctly.")
                sys.exit(1)
            else:
                print("\nEEPROM matches RAM — persistence is working.")

        elif args.reset:
            rresp = reset_settings(conn)
            save_ok = rresp.get("save_ok")
            print("Factory defaults restored:" if save_ok else "EEPROM write FAILED — defaults applied to RAM only:")
            print(_fmt(rresp, eeprom_ok=rresp.get("eeprom_ok"), save_ok=save_ok))
            if not save_ok:
                sys.exit(1)

        elif args.set:
            updates = {}
            for item in args.set:
                if "=" not in item:
                    print(f"Error: expected KEY=VALUE, got {item!r}", file=sys.stderr)
                    sys.exit(1)
                k, v = item.split("=", 1)
                k = k.strip()
                if k not in SETTING_KEYS:
                    print(f"Error: unknown key {k!r}. Valid keys: {', '.join(SETTING_KEYS)}",
                          file=sys.stderr)
                    sys.exit(1)
                try:
                    updates[k] = _coerce(k, v.strip())
                except ValueError as e:
                    print(f"Error: {e}", file=sys.stderr)
                    sys.exit(1)
            sresp = set_settings(conn, updates)
            save_ok = sresp.get("save_ok")
            print("Settings updated:" if save_ok else "RAM updated but EEPROM write FAILED — will not survive reboot:")
            print(_fmt(sresp, eeprom_ok=sresp.get("eeprom_ok"), save_ok=save_ok))
            if not save_ok:
                sys.exit(1)

        elif args.get:
            resp = get_settings(conn)
            print(_fmt(resp, eeprom_ok=resp.get("eeprom_ok")))

        else:
            # No flags — interactive menu
            interactive_menu(conn)

    except (RuntimeError, TimeoutError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
