# src/bootstrap.py

import ctypes
import sys
import os

#from src.logic.project_context import get_active_project_path
from src.core.event_bus import EventBus
from src.core.state import AppState
from src.controller.AppController import AppController

from src.core.config import LOG_DIR, CACHE_DIR, STAGING_DIR, USER_DATA_DIR, APP_ID, IS_BUNDLE, ROOT_DIR
from scripts.generate_tree import update_tree_if_dev
from src.core.logging_config import configure_logging
from src.ui.theme import apply_theme
from src.ui.navigation.register_views import register_views


def bootstrap():
    """Assembles the application and returns the root controller."""
    # 1. Force UTF-8 for cross-platform character support (Wokwi/Serial)
    # 2. Set Windows Identity (Icons/Notifications)
    # 3. Infrastructure Integrity (Create folders BEFORE logging starts)
    # 4. Services Initialization
    os.environ["PYTHONUTF8"] = "1"
    _set_app_id()
    _ensure_directories()
    configure_logging()
    if not IS_BUNDLE:
        update_tree_if_dev(ROOT_DIR)
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