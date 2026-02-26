Import("env")

VID_TOKEN = "1D51"
PID_TOKEN = "ACAB"

# Mapping:
# LOCATION=...:x.0  -> Debug (MI_00)
# LOCATION=...:x.2  -> Bridge (MI_02)
DEBUG_LOC_SUFFIX  = "X.0"
BRIDGE_LOC_SUFFIX = "X.2"
OSC_LOC_SUFFIX    = "X.4"
FUNC_LOC_SUFFIX   = "X.6"

def _ports():
    import serial.tools.list_ports
    return list(serial.tools.list_ports.comports())

def _hwid_upper(p):
    return (getattr(p, "hwid", "") or "").upper()

def _is_our_device(hwid):
    return (VID_TOKEN in hwid) and (PID_TOKEN in hwid)

def _loc_suffix(hwid):
    # hwid example: "USB VID:PID=1D51:ACAB SER=0 LOCATION=1-3:x.2"
    hwid_u = hwid.upper()
    key = "LOCATION="
    i = hwid_u.find(key)
    if i < 0:
        return None
    loc = hwid_u[i + len(key):].strip()   # "1-3:X.2"
    # take part after last ':' -> "X.2"
    if ":" in loc:
        return loc.split(":")[-1].strip()
    return loc

def find_port_by_location(loc_suffix_wanted):
    for p in _ports():
        hwid = _hwid_upper(p)
        if not _is_our_device(hwid):
            continue
        suf = _loc_suffix(hwid)
        if suf == loc_suffix_wanted:
            print("Found:", p.device, "|", p.description, "|", p.hwid)
            return p.device
    return None

def after_upload(source, target, env):
    import time

    debug_port = None
    bridge_port = None

    # Wait for Windows re-enumeration after reboot
    t0 = time.time()
    while time.time() - t0 < 30:
        debug_port  = find_port_by_location(DEBUG_LOC_SUFFIX)
        bridge_port = find_port_by_location(BRIDGE_LOC_SUFFIX)
        osc_fun_port = find_port_by_location(OSC_LOC_SUFFIX)
        if debug_port:
            break
        time.sleep(0.2)

    if not debug_port:
        print(f"timeout: could not find debug port by LOCATION suffix {DEBUG_LOC_SUFFIX}")
        print("---- PORT SNAPSHOT ----")
        for p in _ports():
            print(p.device, "|", p.description, "|", p.hwid)
        print("-----------------------")
        return

    env.Replace(MONITOR_PORT=debug_port)
    print("MONITOR_PORT =", debug_port)
    print("BRIDGE_PORT  =", bridge_port)
    print("OSC_FUN_PORT =", osc_fun_port)

env.AddPostAction("upload", after_upload)