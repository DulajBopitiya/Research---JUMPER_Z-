# src/core/state_ownership.py

from typing import Dict, Final
from src.core.state_keys import StateKeys

"""
Defines which component is authorized to MODIFY specific state keys.
Prevents UI components from accidentally changing system-critical data.
"""

STATE_OWNERSHIP: Final[Dict[StateKeys, str]] = {
    # System Level (Managed by AppController)
    StateKeys.APP_IS_RUNNING: "AppController",
    StateKeys.APP_VERSION: "AppController",
    StateKeys.ACTIVE_VIEW: "AppController",

    # UI Preferences (Usually managed by AppController via Settings)
    StateKeys.CURRENT_THEME: "AppController",
    StateKeys.SIDEBAR_COLLAPSED: "AppController",

    # Hardware State (Strictly AppController/SerialService)
    StateKeys.SERIAL_CONNECTED: "AppController",
    StateKeys.SERIAL_STATUS: "AppController",
    StateKeys.SERIAL_PORT: "AppController",
    StateKeys.SERIAL_BAUDRATE: "AppController",

    # Project Logic (Managed by ProjectContext or AppController)
    StateKeys.PROJECT_FOLDER: "AppController"
}
