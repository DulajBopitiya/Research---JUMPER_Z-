Import("env")

# ---------------------------------------------------------------------------
# find_JumperZ_monitor.py
#
# Pre-action script that auto-detects the JumperZ debug serial port and sets
# MONITOR_PORT before `pio device monitor` opens.
#
# JumperZ exposes 4 CDC interfaces (Windows enumerates 3):
#   CDC 0  "TinyUSB"        location X.0  ← debug / Serial  (this one)
#   CDC 1  "JZ NETSH"       location X.2  ← JSON control
#   CDC 2  "JZ TTL"         location X.4  ← Arduino Nano bridge
#
# The script matches VID=1D51 / PID=ACAB and picks the port whose USB
# location ends in X.0.  If not found it falls back to any matching JumperZ
# port so `pio monitor` still starts rather than failing silently.
# ---------------------------------------------------------------------------

VID_TOKEN      = "1D51"
PID_TOKEN      = "ACAB"
DEBUG_LOC_SUFFIX = "X.0"      # CDC 0 — default Arduino Serial / debug


def _upper(x):
    return (x or "").upper()


def _loc_suffix(hwid: str):
    """Extract the USB interface suffix (e.g. 'X.0', 'X.2') from the HWID string."""
    h = _upper(hwid)
    key = "LOCATION="
    i = h.find(key)
    if i < 0:
        return None
    loc = h[i + len(key):].strip()        # e.g. "1-3:X.0"
    return loc.split(":")[-1].strip() if ":" in loc else loc


def _com_number(dev):
    import re
    if not dev:
        return 10**9
    m = re.search(r"COM(\d+)$", (dev or "").upper())
    return int(m.group(1)) if m else 10**9


def find_monitor_port():
    import serial.tools.list_ports

    debug_matches    = []   # exact X.0 location match
    no_loc_matches   = []   # no LOCATION field — CDC0 on some Windows versions
    fallback_matches = []   # other JumperZ ports (X.2, X.4, X.6 …)

    for p in serial.tools.list_ports.comports():
        dev  = getattr(p, "device",      None)
        desc = getattr(p, "description", None)
        hwid = getattr(p, "hwid",        None)

        # Handle legacy tuple format
        if dev is None and isinstance(p, (list, tuple)) and len(p) >= 3:
            dev, desc, hwid = p[0], p[1], p[2]

        hw = _upper(hwid)
        if VID_TOKEN not in hw or PID_TOKEN not in hw:
            continue

        suf = _loc_suffix(hwid)
        if suf == DEBUG_LOC_SUFFIX:
            debug_matches.append((dev, desc, hwid))
        elif suf is None:
            # No LOCATION in hwid — Windows sometimes omits it for CDC interface 0
            no_loc_matches.append((dev, desc, hwid))
        else:
            fallback_matches.append((dev, desc, hwid))

    # Priority: exact X.0 → no-location (likely CDC 0) → lowest-COM fallback
    if debug_matches:
        candidates, label = debug_matches, "DEBUG (CDC 0, loc X.0)"
    elif no_loc_matches:
        candidates, label = no_loc_matches, "DEBUG (CDC 0, no-location)"
    else:
        candidates, label = fallback_matches, "FALLBACK"

    if not candidates:
        return None

    candidates.sort(key=lambda x: _com_number(x[0]))
    dev, desc, hwid = candidates[0]
    print(f"[JumperZ monitor] Auto-detected {label} port: {dev}  |  {desc}")
    return dev


def set_monitor_port(source, target, env):
    port = find_monitor_port()
    if not port:
        print(
            f"[JumperZ monitor] WARNING: Could not find JumperZ port "
            f"(VID={VID_TOKEN} PID={PID_TOKEN} loc={DEBUG_LOC_SUFFIX}). "
            f"Using platformio.ini default."
        )
        return
    env.Replace(MONITOR_PORT=port)


env.AddPreAction("monitor", set_monitor_port)
