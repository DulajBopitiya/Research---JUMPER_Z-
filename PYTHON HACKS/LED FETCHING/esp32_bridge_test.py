"""
esp32_bridge_test.py
--------------------
Test the RP2040 ↔ ESP32-S3 ↔ STM32 UART bridge.

Modes
-----
(default)   uart_ping — sends {"cmd":"uart_ping"} and watches debug port for
                        "[ESP32] PONG" and heartbeat lines.

--stm DATA  stm_cmd   — sends {"cmd":"stm_cmd","data":DATA} to the STM32 via
                        ESP32.  STM32 replies arrive on the control port as
                        {"type":"stm_data","data":"..."} JSON lines.
                        Also streams debug port so you can see "[STM32] ..."
                        lines printed by the RP2040.

--watch     watch     — skip sending anything, just monitor both ports.

Usage
-----
  python esp32_bridge_test.py                     # ping test
  python esp32_bridge_test.py --stm "#A#"         # send #A# to STM32
  python esp32_bridge_test.py --stm "#A#" --once  # send once, print replies, exit
  python esp32_bridge_test.py --watch             # passive monitor
"""

import argparse
import json
import sys
import threading
import time

import serial
import serial.tools.list_ports

# ── board identifiers ──────────────────────────────────────────────────────────
VID = 0x1D51
PID = 0xACAB


def _location_suffix(port_info) -> str:
    hwid = port_info.hwid or ""
    for part in hwid.split():
        if part.startswith("LOCATION="):
            loc = part.split("=", 1)[1]
            return loc.split(".")[-1]
    return ""   # no LOCATION → treat as CDC 0 (debug)


def find_ports():
    """Return (debug_port, control_port) device strings."""
    debug_port = None
    control_port = None
    for p in serial.tools.list_ports.comports():
        if p.vid != VID or p.pid != PID:
            continue
        suffix = _location_suffix(p)
        if suffix in ("0", ""):     # CDC 0 — debug / Serial
            debug_port = p.device
        elif suffix == "2":         # CDC 1 — JZ NETSH (JSON control)
            control_port = p.device
    return debug_port, control_port


# ── monitor thread — watches debug port (CDC 0) ────────────────────────────────

def monitor_debug(debug_port: str, stop_event: threading.Event):
    try:
        with serial.Serial(debug_port, 115200, timeout=0.5) as ser:
            print(f"[monitor] Opened debug port {debug_port}")
            while not stop_event.is_set():
                try:
                    raw = ser.readline()
                except serial.SerialException as e:
                    print(f"[monitor] Serial error: {e}")
                    break
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("[STM32]"):
                    print(f"\033[96m{line}\033[0m")     # cyan
                elif line.startswith("[ESP32]"):
                    print(f"\033[92m{line}\033[0m")     # green
                else:
                    print(f"[dbg] {line}")
    except serial.SerialException as e:
        print(f"[monitor] Could not open {debug_port}: {e}")


# ── control-port reader — watches CDC 1 for stm_data JSON ─────────────────────

def monitor_control(control_port: str, stop_event: threading.Event):
    """Read unsolicited JSON lines from the control port and print stm_data."""
    try:
        with serial.Serial(control_port, 115200, timeout=0.5) as ser:
            print(f"[stm   ] Watching control port {control_port} for STM32 data…")
            while not stop_event.is_set():
                try:
                    raw = ser.readline()
                except serial.SerialException as e:
                    print(f"[stm   ] Serial error: {e}")
                    break
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get("type") == "stm_data":
                        print(f"\033[95m[STM32 data] {msg['data']}\033[0m")  # magenta
                    else:
                        print(f"[ctrl ] {line}")
                except json.JSONDecodeError:
                    print(f"[ctrl ] (raw) {line}")
    except serial.SerialException as e:
        print(f"[stm   ] Could not open {control_port}: {e}")


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="JumperZ ESP32 / STM32 bridge test")
    parser.add_argument("--stm", metavar="DATA",
                        help="Send DATA to the STM32 via stm_cmd (e.g. '#A#')")
    parser.add_argument("--once", action="store_true",
                        help="With --stm: send once, collect replies for 3 s, then exit")
    parser.add_argument("--watch", action="store_true",
                        help="Just watch — skip sending anything")
    args = parser.parse_args()

    print("Scanning for JumperZ ports…")
    debug_port, control_port = find_ports()

    if not debug_port and not control_port:
        print("ERROR: No JumperZ ports found. Is the board plugged in?")
        sys.exit(1)

    print(f"  Debug port   (CDC 0): {debug_port or 'not found'}")
    print(f"  Control port (CDC 1): {control_port or 'not found'}")
    print()

    stop = threading.Event()

    # Always start the debug monitor
    if debug_port:
        t_dbg = threading.Thread(target=monitor_debug,
                                 args=(debug_port, stop), daemon=True)
        t_dbg.start()

    time.sleep(0.3)   # let the monitor open its port first

    # ── STM32 bridge mode ──────────────────────────────────────────────────────
    if args.stm:
        if not control_port:
            print("ERROR: Control port (CDC 1 / JZ NETSH) not found — needed for stm_cmd.")
            stop.set()
            sys.exit(1)

        if args.once:
            # Send the command, collect stm_data replies for a few seconds, then exit
            with serial.Serial(control_port, 115200, timeout=3) as ctrl:
                cmd = json.dumps({"cmd": "stm_cmd", "data": args.stm}) + "\n"
                ctrl.write(cmd.encode())
                print(f"Sent: {cmd.strip()}")

                # First line back is the ACK
                ack_raw = ctrl.readline()
                if ack_raw:
                    print(f"ACK : {ack_raw.decode('utf-8', errors='replace').strip()}")

                # Collect subsequent stm_data lines for up to 3 s
                print("Waiting for STM32 data (3 s timeout)…")
                deadline = time.time() + 3.0
                while time.time() < deadline:
                    raw = ctrl.readline()
                    if not raw:
                        break
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                        if msg.get("type") == "stm_data":
                            print(f"\033[95m[STM32 data] {msg['data']}\033[0m")
                        else:
                            print(f"[ctrl ] {line}")
                    except json.JSONDecodeError:
                        print(f"[ctrl ] (raw) {line}")

            stop.set()
            return

        else:
            # Streaming mode — send the command once, then watch both ports
            try:
                with serial.Serial(control_port, 115200, timeout=2) as ctrl:
                    cmd = json.dumps({"cmd": "stm_cmd", "data": args.stm}) + "\n"
                    ctrl.write(cmd.encode())
                    print(f"Sent: {cmd.strip()}")
                    ack_raw = ctrl.readline()
                    if ack_raw:
                        print(f"ACK : {ack_raw.decode('utf-8', errors='replace').strip()}")
            except serial.SerialException as e:
                print(f"Could not open control port: {e}")

            # Now start the control-port monitor for ongoing stm_data messages
            t_ctrl = threading.Thread(target=monitor_control,
                                      args=(control_port, stop), daemon=True)
            t_ctrl.start()

    # ── uart_ping mode (default when no --stm / --watch) ──────────────────────
    elif not args.watch:
        if control_port:
            try:
                with serial.Serial(control_port, 115200, timeout=2) as ctrl:
                    cmd = json.dumps({"cmd": "uart_ping"}) + "\n"
                    ctrl.write(cmd.encode())
                    print(f"Sent: {cmd.strip()}")
                    resp_raw = ctrl.readline()
                    if resp_raw:
                        try:
                            resp = json.loads(resp_raw.decode("utf-8", errors="replace"))
                            print(f"Response: {resp}")
                        except json.JSONDecodeError:
                            print(f"Response (raw): {resp_raw}")
            except serial.SerialException as e:
                print(f"Could not open control port: {e}")
        else:
            print("Control port not found — watching debug only.")

    else:
        print("Watch mode — not sending anything. Ctrl+C to stop.")

    print("\nMonitoring (Ctrl+C to stop)…\n")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping.")
        stop.set()


if __name__ == "__main__":
    main()
