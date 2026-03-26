# src/core/logging_config.py

"""
Global logging configuration for JP PLATFORM.

- Two log files:
    - app.log   : INFO+ (user / system friendly)
    - debug.log : DEBUG+ (developer detail; includes file/line and event_id)
- Console output for immediate feedback
- JPLoggerAdapter to add event_id into the 'extra' field of records
- EventIDFilter guarantees %(event_id)s exists in all records to avoid formatting errors
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Final

from src.core.config import APP_LOG_FILE, LOG_DIR

# ================================================================
#                      Component-Type Mapping
# ================================================================
COMPONENT_TYPE_MAP: Final[dict[str, str]] = {
    # Controllers
    "AppController": "CTRL",
    # Views
    "base_frame": "VIEW",
    "dashboard_view": "VIEW",
    "simulations_view": "VIEW",
    "code_editor_view": "VIEW",
    "measurements_view": "VIEW",
    "data_analysis_view": "VIEW",
    "notifications_view": "VIEW",
    "settings_view": "VIEW",
    # UI Components
    "app_shell": "UI",
    "sidebar": "UI",
    # Core Logic
    "task_runner": "CORE",
    "state": "CORE",
    "event_bus": "CORE",
    # Services/Logic Modules
    "project_context": "LOGIC",
}


class EventIDFilter(logging.Filter):
    """Ensures every LogRecord has an 'event_id' to avoid Formatter KeyErrors."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "event_id"):
            record.event_id = "N/A"
        return True


class JPLoggerAdapter(logging.LoggerAdapter):
    """Adapter to ensure 'event_id' is always present in the record extra."""

    def process(self, msg: str, kwargs: dict[str, Any]):
        event_id = kwargs.pop("event_id", "N/A")
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("event_id", event_id)
        return msg, kwargs


def get_logger(name: str) -> JPLoggerAdapter:
    """Return adapted logger with display name: [TYPE:ComponentName]."""
    component = name.split(".")[-1]
    comp_type = COMPONENT_TYPE_MAP.get(component, "GEN")
    display_name = f"{comp_type}:{component}"
    return JPLoggerAdapter(logging.getLogger(display_name), {})


_logging_configured = False  # module-level flag


# -----------------------
# Global Logging Setup
# -----------------------
def configure_logging(console_level: int = logging.INFO):
    """Configure global dual-file logging for JUMPER-Z."""

    global _logging_configured
    if _logging_configured:
        return

    # Paths are now strictly pulled from config.py
    debug_log_path = LOG_DIR / "debug.log"

    # --------------------------
    # Formatters
    # --------------------------
    fmt_app = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] [%(event_id)s] %(message)s", datefmt="%H:%M:%S"
    )

    fmt_debug = logging.Formatter(
        "%(asctime)s [%(levelname)8s] [%(name)-15s] [%(event_id)-10s] %(message)s (%(filename)s:%(lineno)d)",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --------------------------
    # Root Logger Setup
    # --------------------------
    root = logging.getLogger()
    if getattr(root, "_jp_configured", False):
        return

    root.setLevel(logging.DEBUG)
    event_filter = EventIDFilter()

    # 1. Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(console_level)
    ch.setFormatter(fmt_app)
    ch.addFilter(event_filter)
    root.addHandler(ch)

    # 2. App Log (INFO+) - encoding=utf-8 is professional for Windows
    fh_app = logging.FileHandler(APP_LOG_FILE, encoding="utf-8")
    fh_app.setLevel(logging.INFO)
    fh_app.setFormatter(fmt_app)
    fh_app.addFilter(event_filter)
    root.addHandler(fh_app)

    # 3. Debug Log (DEBUG+)
    fh_debug = logging.FileHandler(debug_log_path, encoding="utf-8")
    fh_debug.setLevel(logging.DEBUG)
    fh_debug.setFormatter(fmt_debug)
    fh_debug.addFilter(event_filter)
    root.addHandler(fh_debug)

    _logging_configured = True
    logging.getLogger().info("System logging initialized.", extra={"event_id": "SYS_START"})
