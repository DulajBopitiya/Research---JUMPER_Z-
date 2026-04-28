#!/usr/bin/env python3
"""
osc_stream.py — Trigger-and-stream helper for the JumperZ oscilloscope pipe.

Specifically tailored for the "#A#\\n" workflow:

    1. Open OSC_FUN_PORT (CDC 3, "JZ Oscilloscope" — auto-detected by USB
       LOCATION suffix X.6).
    2. Send the trigger string (default "#A#\\n") to the STM32.  The bytes flow
       Python -> USBSer2 -> RP2040 -> ESP32 UART0 -> ESP32 UART1 (TX=46) ->
       STM32 RX, byte-for-byte.  The trailing \\n is what the STM32 firmware
       uses as the end-of-command marker — strip it with --no-newline if your
       firmware uses a different terminator (e.g. plain "#A#" or "#A#\\r").
    3. Stream everything the STM32 sends back on its TX line — STM32 TX ->
       ESP32 UART1 (RX=45) -> ESP32 UART0 -> RP2040 -> USBSer2 -> here — until
       Ctrl+C.

Usage
-----
    python osc_stream.py                         # send "#A#\\n", stream UTF-8
    python osc_stream.py --trigger "#B#"         # custom trigger ('\\n' added)
    python osc_stream.py --no-newline            # send the trigger as-is
    python osc_stream.py --hex-out               # show bytes as hex
    python osc_stream.py --no-trigger            # listen only, send nothing
    python osc_stream.py --port COM5 --baud 115200
    python osc_stream.py --duration 5            # auto-stop after 5 s
    python osc_stream.py --save out.bin          # also tee bytes to a file
"""

import argparse
import codecs
import sys
import time

from osc_bridge import OscConn


def _decode_text_escapes(s: str) -> bytes:
    return codecs.decode(s, "unicode_escape").encode("latin-1")


def _fmt(data: bytes, hex_out: bool) -> str:
    if hex_out:
        return " ".join(f"{b:02X}" for b in data) + " "
    return data.decode("utf-8", errors="replace")


def stream(port: str | None, baud: int, trigger: bytes | None,
           hex_out: bool, duration: float | None, save_path: str | None):
    save_fp = open(save_path, "ab") if save_path else None

    with OscConn(port=port, baud=baud, timeout=0.05) as conn:
        print(f"[osc_stream] opened {conn.port} @ {baud} baud")

        if trigger:
            conn.write(trigger)
            print(f"[osc_stream] trigger sent ({len(trigger)} byte(s)): "
                  f"{trigger!r}")
        else:
            print("[osc_stream] no trigger — listening only")

        print("[osc_stream] streaming — Ctrl+C to stop\n")

        t_start = time.time()
        total = 0
        try:
            while True:
                if duration is not None and (time.time() - t_start) >= duration:
                    print(f"\n[osc_stream] duration reached ({duration:.1f} s)")
                    break

                data = conn.read_available()
                if data:
                    sys.stdout.write(_fmt(data, hex_out))
                    sys.stdout.flush()
                    if save_fp:
                        save_fp.write(data)
                        save_fp.flush()
                    total += len(data)
                else:
                    time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n[osc_stream] stopping.")
        finally:
            if save_fp:
                save_fp.close()
            elapsed = time.time() - t_start
            rate = total / elapsed if elapsed > 0 else 0.0
            print(f"[osc_stream] {total} byte(s) in {elapsed:.2f} s "
                  f"({rate:.0f} B/s)")


def main():
    ap = argparse.ArgumentParser(
        description="Trigger STM32 (default '#A#') via OSC_FUN_PORT and stream"
                    " the response.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--trigger", default="#A#",
                    help="Trigger string sent to STM32 (default '#A#'; a "
                         "trailing '\\n' is appended automatically — pass "
                         "--no-newline to disable. Supports \\n \\r \\t \\xHH "
                         "escapes.)")
    ap.add_argument("--no-newline", action="store_true",
                    help="Send the trigger verbatim without appending '\\n'.")
    ap.add_argument("--no-trigger", action="store_true",
                    help="Skip the trigger; just listen.")
    ap.add_argument("--hex-out", action="store_true",
                    help="Display incoming bytes as hex instead of UTF-8.")
    ap.add_argument("--port", help="Explicit COM/tty path (default: auto)")
    ap.add_argument("--baud", type=int, default=115200,
                    help="Baud rate (default 115200; must match STM_UART_BAUD"
                         " in firmware)")
    ap.add_argument("--duration", type=float,
                    help="Auto-stop after N seconds (default: until Ctrl+C)")
    ap.add_argument("--save", metavar="PATH",
                    help="Append received bytes to PATH as well")
    args = ap.parse_args()

    trigger: bytes | None = None
    if not args.no_trigger:
        try:
            trigger = _decode_text_escapes(args.trigger)
        except Exception as e:
            print(f"error: bad trigger string: {e}", file=sys.stderr)
            sys.exit(1)
        if not args.no_newline and not trigger.endswith(b"\n"):
            trigger += b"\n"

    try:
        stream(args.port, args.baud, trigger, args.hex_out,
               args.duration, args.save)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
