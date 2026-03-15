import subprocess
import tempfile
import time
from pathlib import Path

import serial

ARDUINO_CLI = "arduino-cli.exe"
PORT = "COM9"   # RP2040 COM port
FQBN = "arduino:avr:nano:cpu=atmega328old"

DUMMY_CODE = r"""
void setup() {
  Serial.begin(115200);
}

void loop() {
  Serial.println("Nano Alive");
  delay(1000);
}
"""

def run(cmd):
    print("\n> " + " ".join(cmd))
    result = subprocess.run(cmd, text=True, capture_output=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result

def create_dummy_sketch_dir() -> Path:
    base = Path(tempfile.mkdtemp(prefix="nano_upload_"))
    name = base.name
    ino = base / f"{name}.ino"
    ino.write_text(DUMMY_CODE, encoding="utf-8")
    print(f"Sketch created: {ino}")
    return base

def send_command(cmd: str, wait_ready: bool = False):
    with serial.Serial(PORT, 115200, timeout=1) as ser:
        time.sleep(0.2)
        ser.reset_input_buffer()
        ser.write((cmd + "\n").encode())
        ser.flush()

        if wait_ready:
            t0 = time.time()
            while time.time() - t0 < 3.0:
                line = ser.readline().decode(errors="ignore").strip()
                if line:
                    print("RP:", line)
                if "READY" in line:
                    return
            raise RuntimeError("Did not receive READY from RP2040")

def main():
    sketch_dir = create_dummy_sketch_dir()

    run([ARDUINO_CLI, "compile", "--fqbn", FQBN, str(sketch_dir)])

    print("\nSwitching RP2040 to upload mode...")
    send_command("@UPLOAD", wait_ready=True)

    print("\nUploading Nano sketch...")
    run([ARDUINO_CLI, "upload", "-p", PORT, "--fqbn", FQBN, str(sketch_dir), "-v"])

    print("\nSwitching RP2040 back to bridge mode...")
    send_command("@BRIDGE", wait_ready=False)

    print("\nDone.")

if __name__ == "__main__":
    main()