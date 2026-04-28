#!/usr/bin/env python3
"""
osc_bridge.py — Host-side tool for the JumperZ oscilloscope / function-gen
                byte pipe.

Architecture
------------
    PC (this script)
        |
        v  USB CDC  ("JZ Oscilloscope" = OSC_FUN_PORT, LOCATION suffix X.6)
    RP2040 USBSer2
        |
        v  PIO UART  (GPIO 18/19 ↔ ESP32 GPIO 44/43, 115200 8N1)
    ESP32 UART0
        |
        v  raw byte forward
    ESP32 UART1 (GPIO 46 RX / 45 TX)
        |
        v  STM32 USART (RX/TX)
    STM32

It is a fully transparent byte pipe.  Anything you write here lands on the
STM32 USART verbatim; anything the STM32 sends appears on this port verbatim.

Usage
-----
    python osc_bridge.py                              # find port, interactive
    python osc_bridge.py --port COM5 --interactive    # explicit port
    python osc_bridge.py --send "FREQ 1000\\n"         # one-shot ASCII send
    python osc_bridge.py --send-hex "DE AD BE EF"     # one-shot binary send
    python osc_bridge.py --watch                      # listen only
    python osc_bridge.py --list                       # enumerate JumperZ ports

Flags
-----
    --port        Explicit COM/tty path. If omitted, auto-detected by location.
    --baud        Serial baud rate (default 115200 — match STM32 firmware).
    --send TEXT   Send ASCII text (supports \\n \\r \\t \\xHH escapes) then watch.
    --send-hex H  Send raw bytes from a hex string ("DE AD BE EF" or "DEADBEEF").
    --watch       Passive — do not send anything, just print incoming bytes.
    --interactive Read commands from stdin; Ctrl-C to exit.
    --hex-out     Print incoming bytes as hex instead of UTF-8.
    --timeout S   Read timeout in seconds (default 0.1).
"""

import argparse
import codecs
import sys
import threading
import time

import serial
import serial.tools.list_ports

from bridge_send import find_osc_port, VID_TOKEN, PID_TOKEN, _upper, _loc_suffix


# ─── connection wrapper ──────────────────────────────────────────────────────

class OscConn:
    """Persistent connection to OSC_FUN_PORT (CDC 3, 'JZ Oscilloscope').

    Use as a context manager or call .close() when done.
    """

    def __init__(self, port: str | None = None, baud: int = 115200,
                 timeout: float = 0.1):
        if port is None:
            port = find_osc_port()
            if not port:
                raise RuntimeError(
                    "OSC_FUN_PORT not found.  Is the board plugged in, and is "
                    "the 'JZ Oscilloscope' CDC enumerated? (Some Windows installs "
                    "drop CDC 3 — check Device Manager.)"
                )
        self.port = port
        self._s = serial.Serial(port, baudrate=baud, timeout=timeout,
                                write_timeout=2)
        time.sleep(0.15)    # Windows CDC settle

    # raw byte API -----------------------------------------------------------
    def write(self, data: bytes) -> int:
        n = self._s.write(data)
        self._s.flush()
        return n

    def read(self, n: int = 1) -> bytes:
        return self._s.read(n)

    def read_available(self) -> bytes:
        """Read every byte already in the OS buffer (non-blocking)."""
        waiting = self._s.in_waiting
        if waiting:
            return self._s.read(waiting)
        return b""

    def close(self):
        if self._s and self._s.is_open:
            self._s.close()

    def __enter__(self):  return self
    def __exit__(self, *_): self.close()


# ─── helpers ────────────────────────────────────────────────────────────────

def _decode_text_escapes(s: str) -> bytes:
    """Interpret \\n, \\r, \\t, \\xHH, \\0, etc. in a command-line string."""
    return codecs.decode(s, "unicode_escape").encode("latin-1")


def _decode_hex(s: str) -> bytes:
    clean = s.replace(" ", "").replace(",", "").replace("-", "").replace(":", "")
    if len(clean) % 2 != 0:
        raise ValueError(f"Hex string has odd length: {s!r}")
    return bytes.fromhex(clean)


def _fmt_incoming(data: bytes, hex_out: bool) -> str:
    if hex_out:
        return " ".join(f"{b:02X}" for b in data)
    return data.decode("utf-8", errors="replace")


def _list_ports():
    found = []
    for p in serial.tools.list_ports.comports():
        hwid = _upper(getattr(p, "hwid", ""))
        if VID_TOKEN in hwid and PID_TOKEN in hwid:
            suf = _loc_suffix(hwid)
            found.append((p.device, suf or "?", p.description or ""))
    if not found:
        print("No JumperZ ports found.")
        return
    print(f"{'Port':<10} {'Suffix':<8} Description")
    print(f"{'-'*10} {'-'*8} {'-'*30}")
    for dev, suf, desc in found:
        label = {"X.0": "Debug", "X.2": "NETSH", "X.4": "TTL",
                 "X.6": "OSC_FUN"}.get(suf, "?")
        print(f"{dev:<10} {suf:<8} [{label}] {desc}")


# ─── reader thread ──────────────────────────────────────────────────────────

def _reader(conn: OscConn, stop: threading.Event, hex_out: bool):
    while not stop.is_set():
        try:
            data = conn.read(256)
        except serial.SerialException as e:
            print(f"\n[reader] serial error: {e}", file=sys.stderr)
            stop.set()
            return
        if not data:
            continue
        sys.stdout.write(_fmt_incoming(data, hex_out))
        sys.stdout.flush()


# ─── modes ──────────────────────────────────────────────────────────────────

def do_watch(conn: OscConn, hex_out: bool):
    print(f"[osc] Watching {conn.port} — Ctrl+C to stop\n")
    stop = threading.Event()
    t = threading.Thread(target=_reader, args=(conn, stop, hex_out), daemon=True)
    t.start()
    try:
        while not stop.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[osc] stopping.")
        stop.set()


def do_send(conn: OscConn, payload: bytes, watch_after: bool, hex_out: bool):
    print(f"[osc] sending {len(payload)} byte(s) to {conn.port}: "
          f"{payload!r}")
    conn.write(payload)
    if watch_after:
        do_watch(conn, hex_out)


def do_interactive(conn: OscConn, hex_out: bool):
    print(f"[osc] Interactive mode on {conn.port}")
    print("  Type text + Enter to send (adds no newline — include \\n yourself).")
    print("  Prefix with 'hex:' to send raw hex bytes (e.g.  hex: DE AD BE EF)")
    print("  Ctrl+C or 'quit' to exit.\n")

    stop = threading.Event()
    t = threading.Thread(target=_reader, args=(conn, stop, hex_out), daemon=True)
    t.start()

    try:
        while not stop.is_set():
            try:
                line = input()
            except EOFError:
                break
            if line.strip().lower() in ("quit", "exit"):
                break
            try:
                if line.startswith("hex:"):
                    payload = _decode_hex(line[4:].strip())
                else:
                    payload = _decode_text_escapes(line)
                conn.write(payload)
            except Exception as e:
                print(f"[osc] send error: {e}", file=sys.stderr)
    except KeyboardInterrupt:
        print()
    finally:
        stop.set()


# ─── entry point ────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="JumperZ OSC_FUN_PORT transparent byte pipe (RP2040 <-> ESP32 <-> STM32)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--port", help="Explicit COM/tty path (default: auto-detect)")
    ap.add_argument("--baud", type=int, default=115200, help="Baud rate (default 115200)")
    ap.add_argument("--send", metavar="TEXT",
                    help=r"Send ASCII text (supports \n \r \t \xHH) then watch")
    ap.add_argument("--send-hex", metavar="HEX",
                    help="Send raw bytes from hex string (e.g. 'DE AD BE EF')")
    ap.add_argument("--watch", action="store_true", help="Passive — listen only")
    ap.add_argument("--interactive", "-i", action="store_true",
                    help="Interactive send/receive")
    ap.add_argument("--hex-out", action="store_true",
                    help="Print incoming bytes as hex")
    ap.add_argument("--timeout", type=float, default=0.1, help="Read timeout (s)")
    ap.add_argument("--list", action="store_true",
                    help="List all JumperZ ports and exit")
    args = ap.parse_args()

    if args.list:
        _list_ports()
        return

    try:
        conn = OscConn(port=args.port, baud=args.baud, timeout=args.timeout)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[osc] opened {conn.port} @ {args.baud} baud")

    try:
        if args.send is not None:
            payload = _decode_text_escapes(args.send)
            do_send(conn, payload, watch_after=True, hex_out=args.hex_out)
        elif args.send_hex is not None:
            payload = _decode_hex(args.send_hex)
            do_send(conn, payload, watch_after=True, hex_out=args.hex_out)
        elif args.interactive:
            do_interactive(conn, args.hex_out)
        else:
            do_watch(conn, args.hex_out)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
