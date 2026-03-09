"""
Pre-build script: patches Adafruit TinyUSB Library after install/update.

Patches applied:
  1. Adafruit_USBD_Device.h  — enlarge _desc_cfg_buffer from 256 to 512 bytes
       4 CDC interfaces need 273 bytes (9-byte header + 4 × 66-byte CDC block).
       The original 256-byte buffer truncates CDC 3, causing it to be dropped.

  2. Adafruit_USBD_CDC.cpp   — guard setStringDescriptor("JZ Serial") in begin()
       The original begin() always overwrites _strid with "JZ Serial", ignoring
       any string set by the user before calling begin(). The patch skips the
       override when the user has already set a custom string (_strid != 0).
"""

Import("env")
import os

LIBDEPS_DIR = os.path.join(env["PROJECT_LIBDEPS_DIR"], env["PIOENV"])
TINYUSB_DIR = os.path.join(LIBDEPS_DIR, "Adafruit TinyUSB Library", "src", "arduino")

PATCHES = [
    {
        "desc": "Enlarge _desc_cfg_buffer 256 → 512 bytes",
        "file": os.path.join(TINYUSB_DIR, "Adafruit_USBD_Device.h"),
        "old":  "  uint8_t _desc_cfg_buffer[256];",
        "new":  "  uint8_t _desc_cfg_buffer[512]; // enlarged: 4 CDCs need 273 bytes (9 + 4*66)",
    },
    {
        "desc": "Guard setStringDescriptor in CDC begin() so user strings are kept",
        "file": os.path.join(TINYUSB_DIR, "Adafruit_USBD_CDC.cpp"),
        "old": (
            "  _instance = _instance_count++;\n"
            "  this->setStringDescriptor(\"JZ Serial\");\n"
            "  TinyUSBDevice.addInterface(*this);"
        ),
        "new": (
            "  _instance = _instance_count++;\n"
            "  // Only set default string if user hasn't pre-set one (_strid == 0 means unset)\n"
            "  if (_strid == 0) {\n"
            "    this->setStringDescriptor(\"JZ Serial\");\n"
            "  }\n"
            "  TinyUSBDevice.addInterface(*this);"
        ),
    },
]


def apply_patches(source, target, env):
    for p in PATCHES:
        filepath = p["file"]

        if not os.path.exists(filepath):
            print(f"[patch] WARNING: file not found — {filepath}")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if p["new"] in content:
            print(f"[patch] already applied: {p['desc']}")
            continue

        if p["old"] not in content:
            print(f"[patch] WARNING: marker not found (library changed?): {p['desc']}")
            continue

        content = content.replace(p["old"], p["new"])
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[patch] applied: {p['desc']}")


env.AddPreAction("$BUILD_DIR/${PROGNAME}.elf", apply_patches)
