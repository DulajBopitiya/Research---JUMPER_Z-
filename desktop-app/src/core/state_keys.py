# src/core/state_keys.py
from enum import Enum

class StateKeys(str, Enum):
    """
    Centralized keys for the Application State.
    Inheriting from 'str' allows for easy JSON serialization and logging.
    """
    # ---- Application Lifecycle ----
    APP_IS_RUNNING = "app_is_running"
    APP_VERSION = "app_version"

    # ---- UI / Theme ----
    CURRENT_THEME = "current_theme"
    SIDEBAR_COLLAPSED = "sidebar_collapsed"

    # ---- Navigation ----
    ACTIVE_VIEW = "active_view"

    # ---- Hardware / Communication ----
    SERIAL_CONNECTED = "serial_connected"
    SERIAL_STATUS = "serial_status"
    SERIAL_PORT = "serial_port"
    SERIAL_BAUDRATE = "serial_baudrate"

    # ---- Project Logic ----
    PROJECT_FOLDER = "project_folder"

