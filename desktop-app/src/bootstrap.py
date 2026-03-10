# src/bootstrap.py

import ctypes
import sys
import os

#from src.logic.project_context import get_active_project_path
from src.core.config import LOG_DIR, CACHE_DIR, STAGING_DIR, USER_DATA_DIR, APP_ID
from src.core.logging_config import configure_logging
from src.core.theme import apply_theme
from src.ui.navigation.register_views import register_views


def bootstrap():
    """
    Initialize the application environment.
    Execution order is critical for system stability.
    """
    # 1. Force UTF-8 for cross-platform character support (Wokwi/Serial)
    os.environ["PYTHONUTF8"] = "1"

    # 2. Set Windows Identity (Icons/Notifications)
    _set_app_id()
    
    # 3. Infrastructure Integrity (Create folders BEFORE logging starts)
    _ensure_directories()

    # 4. Services Initialization
    configure_logging()
    apply_theme()
    register_views()
    #get_active_project_path()

def _ensure_directories():
    """Ensures all writable runtime directories exist."""
    required_folders = [LOG_DIR, CACHE_DIR, STAGING_DIR, USER_DATA_DIR]
    for folder in required_folders:
        folder.mkdir(parents=True, exist_ok=True)

def _set_app_id():
    """Sets Windows AppUserModelID for taskbar grouping and notifications."""
    if sys.platform != "win32":
        return
    try:
        # Using APP_ID imported from config.py for single source of truth
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        # Fail silently if the DLL call is unavailable
        pass