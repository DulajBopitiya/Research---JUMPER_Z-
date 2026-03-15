"""
debug_menu.py — Interactive JumperZ debug menu.

Sends {"cmd":"debug","what":"..."} to the board over the bridge port (JZ NETSH)
and prints the text response directly in this terminal.

Usage:
    python debug_menu.py
"""

import json
import time
import serial
import serial.tools.list_ports

VID_TOKEN          = "1D51"
PID_TOKEN          = "ACAB"
BRIDGE_LOC_SUFFIX  = "X.2"

BAUD = 115200

MENU = """
╔═══════════════════════════════╗
║   JumperZ Debug Menu          ║
╠═══════════════════════════════╣
║  1. Full dump  (all)          ║
║  2. Chip summary              ║
║  3. Chip crosspoint map       ║
║  4. Active paths              ║
║  5. Configured nets           ║
║  0. Exit                      ║
╚═══════════════════════════════╝
"""

CHOICE_MAP = {
    "1": "all",
    "2": "summary",
    "3": "chips",
    "4": "paths",
    "5": "nets",
}


def _find_bridge_port():
    for p in serial.tools.list_ports.comports():
        hwid = (getattr(p, "hwid", "") or "").upper()
        if VID_TOKEN not in hwid or PID_TOKEN not in hwid:
            continue
        key = "LOCATION="
        i = hwid.find(key)
        if i >= 0:
            loc = hwid[i + len(key):].strip()
            suf = loc.split(":")[-1].strip() if ":" in loc else loc
            if suf == BRIDGE_LOC_SUFFIX:
                return p.device
    return None


def _send_debug(port: str, what: str):
    payload = json.dumps({"cmd": "debug", "what": what}, separators=(",", ":")) + "\n"

    with serial.Serial(port, BAUD, timeout=5, write_timeout=2) as s:
        time.sleep(0.15)
        s.write(payload.encode("utf-8"))
        s.flush()

        print()
        # Read lines until we get the JSON ACK (starts with '{')
        # or we time out (readline returns b'' on timeout)
        while True:
            raw = s.readline()
            if not raw:
                print("[timeout — no more data]")
                break

            line = raw.decode("utf-8", errors="replace").rstrip()

            # JSON ACK line — parse and show status, then stop
            if line.startswith("{"):
                try:
                    ack = json.loads(line)
                    status = "OK" if ack.get("ok") else "ERROR"
                    print(f"\n[{status}] what={ack.get('what','?')}")
                except json.JSONDecodeError:
                    print(f"[raw] {line}")
                break
            else:
                print(line)


def main():
    port = _find_bridge_port()
    if not port:
        print("ERROR: JumperZ bridge port not found.")
        print("  Make sure the board is plugged in and firmware is running.")
        return

    print(f"Connected to: {port}")

    while True:
        print(MENU, end="")
        choice = input("Select option: ").strip()

        if choice == "0":
            print("Bye.")
            break

        what = CHOICE_MAP.get(choice)
        if what is None:
            print(f"  Invalid choice '{choice}' — try again.")
            continue

        print(f"  → Sending debug request: what={what}")
        try:
            _send_debug(port, what)
        except serial.SerialException as e:
            print(f"  Serial error: {e}")


if __name__ == "__main__":
    main()
