import json
import time
import serial
import serial.tools.list_ports

# === Change these if you changed USB IDs on firmware ===
VID_TOKEN = "1D51"
PID_TOKEN = "ACAB"

# Windows/pyserial output shows:
#   LOCATION=...:x.0  (debug)
#   LOCATION=...:x.2  (bridge)
DEBUG_LOC_SUFFIX = "X.0"
BRIDGE_LOC_SUFFIX = "X.2"


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


def send_json_line(port: str, payload: dict, baud: int = 115200):
    """Send one JSON line (newline-terminated) to the given serial port."""
    line = json.dumps(payload, separators=(",", ":")) + "\n"

    with serial.Serial(port, baudrate=baud, timeout=1, write_timeout=1) as s:
        time.sleep(0.15)  # small settle for Windows
        s.write(line.encode("utf-8"))
        s.flush()


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