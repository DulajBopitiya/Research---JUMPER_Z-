# src/core/__init__.py
"""
Public API for the core layer.

All other layers import from here, not from individual core files.
This means internal file renames never break callers outside core/.

Usage:
    from src.core import event_bus, app_state, StateKeys
    from src.core import HW, Build, Serial, Terminal, UI, Task, State
"""

from src.core.config import (
    APP_ID,
    APP_NAME,
    APP_VERSION,
    ARDUINO_CLI_PATH,
    ASSET_DIR,
    CACHE_DIR,
    DEFAULT_APPEARANCE_MODE,
    DEFAULT_THEME,
    ICON_FILE,
    IS_BUNDLE,
    IS_WINDOWS,
    LOG_DIR,
    STAGING_DIR,
    TOOLS_DIR,
    USER_CONFIG_PATH,
    USER_DATA_DIR,
    WINDOW_HEIGHT,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_WIDTH,
)
from src.core.event_bus import event_bus
from src.core.events import (
    HW,
    Build,
    Serial,
    State,
    System,
    Terminal,
)
from src.core.log_events import L
from src.core.state import app_state
from src.core.state_keys import StateKeys
from src.core.task_runner import task_runner

__all__ = [
    # Singletons
    "event_bus",
    "app_state",
    "task_runner",
    # State
    "StateKeys",
    # Logging
    "L",
    # Event groups
    "HW",
    "Build",
    "Serial",
    "Terminal",
    "State",
    "System",
    # Config
    "APP_NAME",
    "APP_VERSION",
    "APP_ID",
    "LOG_DIR",
    "CACHE_DIR",
    "STAGING_DIR",
    "USER_DATA_DIR",
    "ASSET_DIR",
    "TOOLS_DIR",
    "ARDUINO_CLI_PATH",
    "USER_CONFIG_PATH",
    "WINDOW_WIDTH",
    "WINDOW_HEIGHT",
    "WINDOW_MIN_WIDTH",
    "WINDOW_MIN_HEIGHT",
    "DEFAULT_APPEARANCE_MODE",
    "DEFAULT_THEME",
    "ICON_FILE",
    "IS_WINDOWS",
    "IS_BUNDLE",
]
