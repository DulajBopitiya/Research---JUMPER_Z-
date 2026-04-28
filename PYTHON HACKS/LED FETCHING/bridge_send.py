import json
import time
import serial
import serial.tools.list_ports

# === Change these if you changed USB IDs on firmware ===
VID_TOKEN = "1D51"
PID_TOKEN = "ACAB"

# Windows/pyserial output shows:
#   LOCATION=...:x.0  (debug   — CDC 0, "JZ Serial")
#   LOCATION=...:x.2  (bridge  — CDC 1, "JZ NETSH")
#   LOCATION=...:x.4  (ttl     — CDC 2, "JZ TTL"  → Nano)
#   LOCATION=...:x.6  (osc/fn  — CDC 3, "JZ Oscilloscope" → STM32 via ESP32)
DEBUG_LOC_SUFFIX = "X.0"
BRIDGE_LOC_SUFFIX = "X.2"
TTL_LOC_SUFFIX = "X.4"
OSC_LOC_SUFFIX = "X.6"


def _upper(x):
    return (x or "").upper()


def _loc_suffix(hwid: str):
    h = _upper(hwid)
    key = "LOCATION="
    i = h.find(key)
    if i < 0:
        return None
    loc = h[i + len(key):].strip()  # e.g. "1-3:X.2"
    return loc.split(":")[-1].strip() if ":" in loc else loc


def find_ports():
    """Return (debug_port, bridge_port) as COM strings or None."""
    debug_port = None
    bridge_port = None

    for p in serial.tools.list_ports.comports():
        hwid = _upper(getattr(p, "hwid", ""))
        if VID_TOKEN not in hwid or PID_TOKEN not in hwid:
            continue

        suf = _loc_suffix(hwid)
        if suf == DEBUG_LOC_SUFFIX:
            debug_port = p.device
        elif suf == BRIDGE_LOC_SUFFIX:
            bridge_port = p.device

    return debug_port, bridge_port


def find_osc_port():
    """Return the COM string of the OSC_FUN_PORT (CDC 3, "JZ Oscilloscope").

    This is the transparent byte pipe to the STM32 via the ESP32-S3.  Returns
    None if the port isn't enumerated (some Windows installs drop CDC 3).
    """
    for p in serial.tools.list_ports.comports():
        hwid = _upper(getattr(p, "hwid", ""))
        if VID_TOKEN not in hwid or PID_TOKEN not in hwid:
            continue
        if _loc_suffix(hwid) == OSC_LOC_SUFFIX:
            return p.device
    return None


def find_ttl_port():
    """Return the COM string of the Nano TTL port (CDC 2, "JZ TTL"), or None."""
    for p in serial.tools.list_ports.comports():
        hwid = _upper(getattr(p, "hwid", ""))
        if VID_TOKEN not in hwid or PID_TOKEN not in hwid:
            continue
        if _loc_suffix(hwid) == TTL_LOC_SUFFIX:
            return p.device
    return None


def send_json_line(port: str, payload: dict, baud: int = 115200):
    """Send one JSON line (newline-terminated) to the given serial port."""
    line = json.dumps(payload, separators=(",", ":")) + "\n"
    print(f"  [send] {len(line)} bytes to {port}")

    with serial.Serial(port, baudrate=baud, timeout=2, write_timeout=2) as s:
        time.sleep(0.15)  # small settle for Windows
        s.write(line.encode("utf-8"))
        s.flush()
        # Read the board's JSON response (ends with newline)
        resp_line = s.readline()
        if resp_line:
            print(f"  [recv] {resp_line.decode('utf-8', errors='replace').strip()}")


def send_wokwi_wires(wires: list, prefer_bridge=True):
    """Send wires list to bridge port by default."""
    dbg, brg = find_ports()
    target = brg if prefer_bridge else dbg

    if not target:
        raise RuntimeError(
            f"Could not find {'BRIDGE' if prefer_bridge else 'DEBUG'} port. "
            f"Found debug={dbg}, bridge={brg}."
        )

    payload = {
        "cmd": "wokwi_wires",
        "wires": wires,
    }

    send_json_line(target, payload)
    return target


def send_connect_netlist(nets: list, prefer_bridge=True):
    """
    Send a 'connect' netlist command to the board, which closes real CH446Q
    switches in addition to lighting LEDs.

    nets: list of {"nodes": ["TOP_5", "BOTTOM_3", ...], "color": "#rrggbb"}
          as returned by netlist.build_jz_nets().
    """
    dbg, brg = find_ports()
    target = brg if prefer_bridge else dbg

    if not target:
        raise RuntimeError(
            f"Could not find {'BRIDGE' if prefer_bridge else 'DEBUG'} port. "
            f"Found debug={dbg}, bridge={brg}."
        )

    payload = {
        "cmd": "connect",
        "nets": nets,
    }

    send_json_line(target, payload)
    return target


def send_connect_then_wires(nets: list, wires: list, prefer_bridge=True,
                            settle_ms: int = 600):
    """
    Two-step send for full visual + physical switching:
      1. 'connect'     — closes CH446Q switches (physical connections)
      2. 'wokwi_wires' — paints the full LED wire paths

    settle_ms: wait between the two commands so the board finishes the
               path-mapping pipeline before the LED repaint arrives.
    """
    dbg, brg = find_ports()
    target = brg if prefer_bridge else dbg

    if not target:
        raise RuntimeError(
            f"Could not find {'BRIDGE' if prefer_bridge else 'DEBUG'} port. "
            f"Found debug={dbg}, bridge={brg}."
        )

    send_json_line(target, {"cmd": "connect", "nets": nets})
    time.sleep(settle_ms / 1000.0)
    send_json_line(target, {"cmd": "wokwi_wires", "wires": wires})
    return target