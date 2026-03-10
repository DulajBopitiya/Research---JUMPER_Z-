# src/core/logging_event_registry.py

from dataclasses import dataclass
from typing import Final

"""
Central registry for structured logging event IDs.
Format: <PREFIX><LEVEL><3-digit number>
Example: UI201 -> UI (Module), 2 (INFO), 01 (Sequence)
"""

@dataclass(frozen=True)
class Level:
    DEBUG: Final[str]    = "1"
    INFO: Final[str]     = "2"
    WARNING: Final[str]  = "3"
    ERROR: Final[str]    = "4"
    CRITICAL: Final[str] = "5"

@dataclass(frozen=True)
class UIEvents:
    # --- Lifecycle ---
    APP_STARTED: Final[str]           = f"UI{Level.INFO}01"
    APP_READY: Final[str]             = f"UI{Level.INFO}02"
    APP_SHUTDOWN: Final[str]          = f"UI{Level.INFO}03"

    # --- Theme / Resources ---
    ICON_LOADED: Final[str]           = f"UI{Level.DEBUG}01"
    COMPONENT_INITIALIZED: Final[str] = f"UI{Level.DEBUG}02"
    THEME_CHANGED: Final[str]         = f"UI{Level.INFO}04"
    SIDEBAR_TOGGLED: Final[str]       = f"UI{Level.INFO}05"
    STATUS_MESSAGE: Final[str]        = f"UI{Level.INFO}06"
    
    ICON_LOAD_FAILED: Final[str]      = f"UI{Level.WARNING}01"
    IMAGE_LOAD_FAILED: Final[str]     = f"UI{Level.WARNING}02"
    APP_THEME_WARNING: Final[str]     = f"UI{Level.WARNING}03"
    NAVIGATION_DENIED: Final[str]     = f"UI{Level.WARNING}04"
    
    APP_THEME_ERROR: Final[str]       = f"UI{Level.ERROR}01"

@dataclass(frozen=True)
class VWEvents:
    VIEW_CREATED: Final[str]          = f"VW{Level.DEBUG}01"
    VIEW_SHOWN: Final[str]            = f"VW{Level.INFO}01"
    VIEW_HIDDEN: Final[str]           = f"VW{Level.DEBUG}02"
    BUTTON_CLICKED: Final[str]        = f"VW{Level.INFO}02"
    
    VIEW_RENDER_FAILED: Final[str]    = f"VW{Level.ERROR}01"

@dataclass(frozen=True)
class ACEvents:
    CONTROLLER_INIT: Final[str]       = f"AC{Level.INFO}01"
    CONTROLLER_READY: Final[str]      = f"AC{Level.INFO}02"
    NAVIGATION_ALLOWED: Final[str]    = f"AC{Level.INFO}03"
    SHUTDOWN_REQUESTED: Final[str]    = f"AC{Level.INFO}04"

    # --- Serial / Hardware ---
    SERIAL_CONNECT_REQ: Final[str]    = f"AC{Level.INFO}05"
    SERIAL_CONNECTED: Final[str]      = f"AC{Level.INFO}06"
    SERIAL_DISCONNECTED: Final[str]   = f"AC{Level.INFO}07"
    
    SERIAL_PORT_BUSY: Final[str]      = f"AC{Level.WARNING}01"
    SERIAL_CONNECT_FAILED: Final[str] = f"AC{Level.ERROR}01"
    SERIAL_READ_FAILED: Final[str]    = f"AC{Level.ERROR}02"
    SERIAL_WRITE_FAILED: Final[str]   = f"AC{Level.ERROR}03"
    
    UNHANDLED_EXCEPTION: Final[str]   = f"AC{Level.CRITICAL}01"

@dataclass(frozen=True)
class LOGICEvents:
    """Specific to Wokwi, Arduino-CLI, and Project logic."""
    PROJECT_LOADED: Final[str]        = f"LG{Level.INFO}01"
    WOKWI_FETCH_START: Final[str]     = f"LG{Level.INFO}02"
    WOKWI_FETCH_SUCCESS: Final[str]   = f"LG{Level.INFO}03"
    
    CLI_ENGINE_READY: Final[str]      = f"LG{Level.INFO}04"
    CLI_COMPILE_START: Final[str]     = f"LG{Level.INFO}05"
    
    WOKWI_FETCH_FAILED: Final[str]    = f"LG{Level.ERROR}01"
    CLI_COMPILE_FAILED: Final[str]    = f"LG{Level.ERROR}02"

@dataclass(frozen=True)
class COREEvents:
    # TaskRunner
    TASK_STARTED: Final[str]          = f"CR-T{Level.DEBUG}01"
    TASK_COMPLETED: Final[str]        = f"CR-T{Level.INFO}01"
    TASK_FAILED: Final[str]           = f"CR-T{Level.ERROR}01"

    # StateManager
    STATE_CHANGED: Final[str]         = f"CR-S{Level.INFO}01"
    STATE_RESET: Final[str]           = f"CR-S{Level.INFO}02"
    STATE_VIOLATION: Final[str]       = f"CR-S{Level.ERROR}01"

    # EventBus
    EVENT_EMITTED: Final[str]         = f"CR-E{Level.DEBUG}01"
    EVENT_SUBSCRIBED: Final[str]       = f"CR-E{Level.DEBUG}02"
    EVENT_SUBSCRIBED_ONCE: Final[str]  = f"CR-E{Level.DEBUG}03"
    EVENT_UNSUBSCRIBED: Final[str]     = f"CR-E{Level.DEBUG}04"
    EVENT_CLEARED: Final[str]          = f"CR-E{Level.DEBUG}05"
    EVENT_MISSING_LISTENER: Final[str]   = f"CR-E{Level.DEBUG}06"
    EVENT_HANDLER_ERROR: Final[str]   = f"CR-E{Level.ERROR}01"

# --- Static Instances ---
L: Final[Level] = Level()
UI: Final[UIEvents] = UIEvents()
VW: Final[VWEvents] = VWEvents()
AC: Final[ACEvents] = ACEvents()
LG: Final[LOGICEvents] = LOGICEvents()
CR: Final[COREEvents] = COREEvents()