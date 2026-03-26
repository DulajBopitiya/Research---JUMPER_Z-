# src/core/config.py

import platform
import os
import sys
from pathlib import Path
from typing import Final

# ================================================================
#                      PATH STRATEGY
# ================================================================

# Detect if running as a bundled EXE (PyInstaller) or raw Python
IS_BUNDLE: Final[bool] = getattr(sys, 'frozen', False)

if IS_BUNDLE:
    # Production Pathing
    # Path to the .exe location and the temporary bundle directory %LOCALAPPDATA%
    _root_dir   = Path(sys.executable).parent.resolve()
    _bundle_dir = Path(sys._MEIPASS).resolve()  # type: ignore[attr-defined]
    if platform.system() == "Windows":
        _data_base = Path(os.getenv("LOCALAPPDATA", str(_root_dir))) / "JumperZ"
    else:
        _data_base = Path.home() / ".jumperz"

else:
    # Development Pathing
    # resolve().parents[2] gets us from src/core/config.py -> root
    _root_dir   = Path(__file__).resolve().parents[2]
    _bundle_dir = _root_dir
    _data_base  = _root_dir / "runtime_dev"

ROOT_DIR  : Final[Path] = _root_dir
BUNDLE_DIR: Final[Path] = _bundle_dir
DATA_BASE : Final[Path] = _data_base

# --- Writable Locations ---
RUNTIME_DIR: Final[Path] = DATA_BASE / "runtime"
LOG_DIR: Final[Path]    = RUNTIME_DIR / "logs"
CACHE_DIR: Final[Path]  = RUNTIME_DIR / "cache"
STAGING_DIR: Final[Path] = RUNTIME_DIR / "staging"
USER_DATA_DIR: Final[Path] = DATA_BASE / "config"

# --- Static Locations ---
ASSET_DIR: Final[Path] = BUNDLE_DIR / "assets"
TOOLS_DIR: Final[Path] = BUNDLE_DIR / "tools"
STATIC_CONFIG_DIR: Final[Path] = BUNDLE_DIR / "config"

# --- Specific File Handles ---
ARDUINO_CLI_PATH: Final[Path] = TOOLS_DIR / "arduino-cli.exe"
LANGUAGE_CONFIG_PATH: Final[Path] = STATIC_CONFIG_DIR / "language_config.json"
USER_CONFIG_PATH: Final[Path] = USER_DATA_DIR / "user_config.json"
APP_LOG_FILE: Final[Path] = LOG_DIR / "app.log"

# ================================================================
#                     FILE EXTENSIONS / SAVE TYPES
# ================================================================
#DEFAULT_PROJECT_EXTENSION = ".jpprj"
#ALLOWED_DATA_EXPORTS = {".csv", ".json", ".txt"}

# ================================================================
#                     APP CONFIGURATION
# ================================================================

# App Identity
APP_NAME: Final[str] = "JUMPER-Z"    # !!!!! PLEASE CHANGE THIS NAME !!!!!
APP_VERSION: Final[str] = "1.0.0"
APP_ID: Final[str] = "jumperz.research.desktopapp.v1"

#APP_AUTHOR: Final[str] = "Your Name or Company"

# Platform Information
IS_WINDOWS: Final[bool] = platform.system() == "Windows"
#IS_MAC: Final[bool] = platform.system() == "Darwin"
#IS_LINUX: Final[bool] = platform.system() == "Linux"

# UI / Window Settings
WINDOW_WIDTH: Final[int]      = 1200
WINDOW_HEIGHT: Final[int]     = 700
WINDOW_MIN_WIDTH: Final[int]  = 800
WINDOW_MIN_HEIGHT: Final[int] = 500

DEFAULT_APPEARANCE_MODE: Final[str] = "dark"    # options: "dark", "light", "system"
DEFAULT_THEME: Final[str] = "blue"
ICON_FILE: Final[Path] = ASSET_DIR / "sample_app_icon.png"
