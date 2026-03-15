# src/core/log_events.py

from enum import Enum
from tkinter import E

"""
Central registry for structured logging event IDs.

Format:
    <MODULE><LEVEL><SEQ>

Examples:
    UI201   -> UI module, INFO level, event 01
    CR-S401 -> Core State, ERROR level, event 01
"""

class LogLevel(str, Enum):
    DEBUG = "1"
    INFO = "2"
    WARNING = "3"
    ERROR = "4"
    CRITICAL = "5"

class UILogEvents:
    APP_STARTED = f"UI{LogLevel.INFO.value}01"
    APP_READY = f"UI{LogLevel.INFO.value}02"
    APP_SHUTDOWN = f"UI{LogLevel.INFO.value}03"

    # --- Theme / Resources ---
    ICON_LOADED = f"UI{LogLevel.DEBUG.value}01"
    COMPONENT_INITIALIZED = f"UI{LogLevel.DEBUG.value}02"
    THEME_CHANGED = f"UI{LogLevel.INFO.value}04"
    SIDEBAR_TOGGLED = f"UI{LogLevel.INFO.value}05"


    ICON_LOAD_FAILED = f"UI{LogLevel.WARNING.value}01"
    IMAGE_LOAD_FAILED = f"UI{LogLevel.WARNING.value}02"
    APP_THEME_WARNING = f"UI{LogLevel.WARNING.value}03"
    NAVIGATION_ALLOWED = f"UI{LogLevel.INFO.value}04"
    NAVIGATION_DENIED = f"UI{LogLevel.WARNING.value}05"
    
    APP_THEME_ERROR = f"UI{LogLevel.ERROR.value}01"

class VWEvents:
    VIEW_CREATED          = f"VW{LogLevel.DEBUG.value}01"
    VIEW_SHOWN            = f"VW{LogLevel.INFO.value}01"
    VIEW_HIDDEN           = f"VW{LogLevel.DEBUG.value}02"
    BUTTON_CLICKED        = f"VW{LogLevel.INFO.value}02"
    
    VIEW_RENDER_FAILED    = f"VW{LogLevel.ERROR.value}01"

class ACEvents:
    CONTROLLER_INIT       = f"AC{LogLevel.INFO.value}01"
    CONTROLLER_READY      = f"AC{LogLevel.INFO.value}02"
    NAVIGATION_ALLOWED    = f"AC{LogLevel.INFO.value}03"
    SHUTDOWN_REQUESTED    = f"AC{LogLevel.INFO.value}04"

    # --- Serial / Hardware ---
    SERIAL_CONNECT_REQ    = f"AC{LogLevel.INFO.value}05"
    SERIAL_CONNECTED      = f"AC{LogLevel.INFO.value}06"
    SERIAL_DISCONNECTED   = f"AC{LogLevel.INFO.value}07"

    SERIAL_PORT_BUSY      = f"AC{LogLevel.WARNING.value}01"
    SERIAL_CONNECT_FAILED = f"AC{LogLevel.ERROR.value}01"
    SERIAL_READ_FAILED    = f"AC{LogLevel.ERROR.value}02"
    SERIAL_WRITE_FAILED   = f"AC{LogLevel.ERROR.value}03"
    
    UNHANDLED_EXCEPTION   = f"AC{LogLevel.CRITICAL.value}01"


class LOGICLogEvents:
    """Specific to Wokwi, Arduino-CLI, and Project logic."""
    PROJECT_LOADED        = f"LG{LogLevel.INFO.value}01"
    WOKWI_FETCH_START     = f"LG{LogLevel.INFO.value}02"
    WOKWI_FETCH_SUCCESS   = f"LG{LogLevel.INFO.value}03"
    
    CLI_ENGINE_READY      = f"LG{LogLevel.INFO.value}04"
    CLI_COMPILE_START     = f"LG{LogLevel.INFO.value}05"
    
    WOKWI_FETCH_FAILED    = f"LG{LogLevel.ERROR.value}01"
    CLI_COMPILE_FAILED    = f"LG{LogLevel.ERROR.value}02"

class CORELogEvents:
    # TaskRunner
    TASK_STARTED = f"CR-T{LogLevel.DEBUG.value}01"
    TASK_COMPLETED = f"CR-T{LogLevel.INFO.value}01"
    TASK_FAILED = f"CR-T{LogLevel.ERROR.value}01"

    # StateManager
    STATE_CHANGED = f"CR-S{LogLevel.INFO.value}01"
    STATE_RESET = f"CR-S{LogLevel.INFO.value}02"
    STATE_VIOLATION = f"CR-S{LogLevel.ERROR.value}01"

    # EventBus
    EVENT_EMITTED = f"CR-E{LogLevel.DEBUG.value}01"
    EVENT_SUBSCRIBED = f"CR-E{LogLevel.DEBUG.value}02"
    EVENT_SUBSCRIBED_ONCE = f"CR-E{LogLevel.DEBUG.value}03"
    EVENT_UNSUBSCRIBED     = f"CR-E{LogLevel.DEBUG.value}04"
    EVENT_LOOP_REGISTERED = f"CR-E{LogLevel.DEBUG.value}02"
    EVENT_CLEARED          = f"CR-E{LogLevel.DEBUG.value}05"
    EVENT_MISSING_LISTENER   = f"CR-E{LogLevel.DEBUG.value}06"
    EVENT_HANDLER_ERROR   = f"CR-E{LogLevel.ERROR.value}01"

class LogEvents:
    UI = UILogEvents()
    VW = VWEvents()
    AC = ACEvents()
    LOGIC = LOGICLogEvents()
    CORE = CORELogEvents()

# Import alias
L = LogEvents