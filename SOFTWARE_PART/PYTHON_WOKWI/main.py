import os
import re
import sys
import json
import time
import shutil
import tempfile
import subprocess
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---- USER INPUT: your Wokwi project URL ----
# WOKWI_URL = "https://wokwi.com/projects/new/esp32-s3"
WOKWI_URL ="https://wokwi.com/projects/451651671857283073"

# ---- Settings (change if needed) ----
FQBN = "esp32:esp32:esp32s3"  # generic ESP32 Dev Module (Arduino core)
SKETCH_NAME = "wokwi_esp32_project"  # folder + ino name
ARDUINO_CLI = "arduino-cli.exe"  # path or just name if in PATH

def run(cmd, check=True, capture=False):
    print(f"\n> {cmd}")
    res = subprocess.run(cmd, shell=True, check=check,
                         stdout=subprocess.PIPE if capture else None,
                         stderr=subprocess.STDOUT if capture else None,
                         text=True)
    return res.stdout if capture else ""

def ensure_core():
    # Make sure esp32 core is installed (idempotent)
    try:
        print("\nChecking ESP32 core...")
        out = run(f"{ARDUINO_CLI} core list", capture=True)
        if "esp32:esp32" not in out:
            print("Installing esp32:esp32 core...")
            run(f"{ARDUINO_CLI} core update-index")
            run(f"{ARDUINO_CLI} core install esp32:esp32")
        else:
            print("ESP32 core already installed.")
    except subprocess.CalledProcessError as e:
        print(e.stdout or str(e))
        sys.exit("arduino-cli not found or failed. Please install/configure Arduino CLI first.")

def fetch_sketch_text(project_url: str) -> str:
    """
    Fetch the Wokwi project page and try to extract the 'sketch.ino' text.
    For most public projects, the code is directly present in the HTML.
    """
    print(f"\nFetching Wokwi page: {project_url}")
    r = requests.get(project_url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Heuristic 1: look for a code block directly on the page (common on public projects)
    # We scan <pre> tags after a 'sketch.ino' marker.
    html_text = r.text
    if "sketch.ino" in html_text:
        # Try to find a <pre> that contains code (Wokwi renders code as text in page source for many public projects)
        pres = soup.find_all("pre")
        best = None
        for pre in pres:
            text = pre.get_text("\n", strip=False)
            # Assume at least a couple of includes or setup/loop markers indicate the code block
            if "#include" in text or "void setup" in text or "void loop" in text or "setup()" in text:
                best = text
                break
        if best:
            print("Found sketch code inside page HTML.")
            return best

    # Heuristic 2: try fetching diagram.json and see if the project references files (you could extend this if needed)
    # Many projects still require manual export for full file list, but diagram.json is always available.
    m = re.search(r"/projects/(\d+)", project_url)
    if m:
        project_id = m.group(1)
        dj_url = f"https://wokwi.com/api/projects/{project_id}/diagram.json"
        print(f"Trying diagram.json: {dj_url}")
        dj = requests.get(dj_url, timeout=30)
        if dj.status_code == 200:
            # You could parse it if your flow needs pin mapping, but it doesn't embed the code.
            print("diagram.json downloaded (but it does not contain code).")
        else:
            print("diagram.json not accessible.")
    raise RuntimeError("Could not extract sketch code automatically. "
                       "If this is a private project or uses non-arduino files, export manually from Wokwi.")

def create_arduino_sketch_dir(sketch_code: str) -> Path:
    tmpdir = Path(tempfile.mkdtemp(prefix="wokwi_esp32_"))
    sketch_dir = tmpdir / SKETCH_NAME
    sketch_dir.mkdir(parents=True, exist_ok=True)
    ino_path = sketch_dir / f"{SKETCH_NAME}.ino"
    ino_path.write_text(sketch_code, encoding="utf-8")
    print(f"\nSketch saved to: {ino_path}")
    return sketch_dir

def detect_port(preferred: str | None = None) -> str:
    print("\nDetecting boards/ports via arduino-cli...")
    out = run(f"{ARDUINO_CLI} board list", capture=True)
    print(out)

    # collect ports from the first column of each data row
    ports = []
    for line in out.splitlines():
        # match start-of-line COMx or /dev/tty*
        m = re.match(r'^(COM\d+|/dev/tty\S+)\b', line.strip())
        if m:
            ports.append(m.group(1))

    if not ports:
        sys.exit("Could not find a serial port. Plug your ESP32 and ensure drivers are installed.")

    # allow manual override (env var or function arg)
    env_pref = os.getenv("ESP32_PORT")
    preferred = preferred or env_pref
    if preferred and preferred in ports:
        port = preferred
    else:
        # pick the first detected if no/invalid preference
        port = ports[0]

    print(f"Using port: {port}")
    return port


def compile_and_upload(sketch_dir: Path, port: str):
    print("\nCompiling...")
    run(f'{ARDUINO_CLI} compile --fqbn {FQBN} "{sketch_dir}"')

    print("\nUploading...")
    run(f'{ARDUINO_CLI} upload -p {port} --fqbn {FQBN} "{sketch_dir}"')

    print("\nDone. If your sketch prints to Serial, open a monitor, e.g.:")
    print(f'{ARDUINO_CLI} monitor -p {port} -c baudrate=115200')

def main():
    ensure_core()
    code = fetch_sketch_text(WOKWI_URL)
    sketch_dir = create_arduino_sketch_dir(code)
    port = detect_port(preferred="COM5")
    compile_and_upload(sketch_dir, port)

if __name__ == "__main__":
    main()
