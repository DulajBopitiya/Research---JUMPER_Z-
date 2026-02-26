Import("env")

VID_TOKEN = "1D51"
PID_TOKEN = "ACAB"

# If you want a specific interface for upload, set this.
# For most cases, upload uses only one of them; pick MI_00 by default.
UPLOAD_MI = "MI_00"

def _iter_ports():
    import serial.tools.list_ports
    for p in serial.tools.list_ports.comports():
        # p is usually a ListPortInfo object
        dev  = getattr(p, "device", None)
        desc = getattr(p, "description", None)
        hwid = getattr(p, "hwid", None)

        # fallback if tuple style (port, desc, hwid)
        if dev is None and isinstance(p, (list, tuple)) and len(p) >= 3:
            dev, desc, hwid = p[0], p[1], p[2]
        yield dev, desc, hwid

def _com_number(dev):
    # Parse COM number safely (COM3 -> 3, COM12 -> 12)
    import re
    if not dev:
        return 10**9
    m = re.search(r"COM(\d+)$", dev.upper())
    return int(m.group(1)) if m else 10**9

def find_upload_port():
    matches = []
    for dev, desc, hwid in _iter_ports():
        hw = (hwid or "").upper()

        if (VID_TOKEN in hw) and (PID_TOKEN in hw):
            # If you want to force a specific interface, require MI token
            if UPLOAD_MI and (UPLOAD_MI not in hw):
                continue
            matches.append((dev, desc, hwid))

    if not matches:
        return None

    # Choose the lowest COM number so it’s stable
    matches.sort(key=lambda x: _com_number(x[0]))
    chosen = matches[0]
    print("Autodetected UPLOAD port:", chosen[0], "|", chosen[1], "|", chosen[2])
    return chosen[0]

def find_jumperless_port_upload(source, target, env):
    port = find_upload_port()
    if not port:
        print(f"Could not find upload port (VID={VID_TOKEN} PID={PID_TOKEN} {UPLOAD_MI})")
        return
    env.Replace(UPLOAD_PORT=port)

env.AddPreAction("upload", find_jumperless_port_upload)