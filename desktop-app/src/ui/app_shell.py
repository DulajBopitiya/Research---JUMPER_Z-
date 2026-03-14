# src/ui/app_shell.py 

import customtkinter as ctk
from PIL import Image, ImageTk

from src.core.event_bus import event_bus
from src.core.events import Events
from src.core.state import app_state
from src.core.state_keys import StateKeys
from src.core.logging_config import get_logger
from src.core.log_events import L
from src.utils.resource_path import resource_path 

# ---- Import Configuration ----
from src.core.config import (
    APP_NAME, APP_VERSION, 
    WINDOW_WIDTH, WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    ICON_FILE
)

# --- UI Components ---
from src.ui.components.sidebar import SideBar

# Navigation system
from src.ui.navigation.navigation_host import NavigationHost
from src.ui.navigation.router import Router

# Controller
from src.controller.AppController import AppController

logger = get_logger(__name__)

class AppShell(ctk.CTk):
    """
    Root Application Window.

    Responsibilities
    -----------------
    • Owns the main window
    • Creates application layout
    • Bootstraps navigation system
    • Initializes controller

    Forbidden
    ----------
    • Business logic
    • Navigation policy
    • State mutation
    """
   
    def __init__(self):
        super().__init__()
        
        logger.info("Application starting", extra={"event_id": L.UI.APP_STARTED})

        # --- Window Setup ---
        self._configure_window()
        
        # --- Controller ---
        self.app_controller = AppController()

        # Layout
        self._configure_grid()

        self.sidebar = SideBar(self)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        
        # Navigation host
        self.nav_host = NavigationHost(self)
        self.nav_host.grid(row=0, column=1, sticky="nsew")

        # Router
        self.router = Router(self.nav_host)

       # ---  Initial state sync ---
        self._sync_initial_state()

        logger.info("Application ready", extra={"event_id": L.UI.APP_READY})

    # =====================================================
    # Window Setup
    # =====================================================
    def _configure_window(self):
        self.title(f" {APP_NAME}  v{APP_VERSION}")

        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}") 
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self._load_app_icon()

    # ------------------------------
    # Internal helper methods
    # ------------------------------
    def _load_app_icon(self):
        """Load application icon safely."""
        try:
            icon_path = resource_path(str(ICON_FILE))

            pil_img = Image.open(icon_path).convert("RGBA")
            self._icon_reference = ImageTk.PhotoImage(pil_img)
            
            self.after(200, lambda: self.iconphoto(False, self._icon_reference))
            logger.debug("Application icon loaded from", extra={"event_id": L.UI.ICON_LOADED})
        except Exception as e:
            logger.warning("Failed to load application icon: %s", e, extra={"event_id": L.UI.ICON_LOAD_FAILED})


    def _configure_grid(self):
        self.grid_rowconfigure(0, weight=1)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

    # --------------------------------------------------
    # Initial state sync
    # --------------------------------------------------
    def _sync_initial_state(self):
        # Sidebar
        #collapsed = app_state.get(StateKeys.SIDEBAR_COLLAPSED, True)
        #event_bus.emit(Events.UI.SIDEBAR_STATE_CHANGED, collapsed=collapsed)

        # Navigation
        initial_view = app_state.get(StateKeys.ACTIVE_VIEW, "Home")
        event_bus.emit(Events.UI.NAVIGATION_REQUESTED, target=initial_view)

    # ======================================================
    # Shutdown hook (future-safe)
    # ======================================================
    def destroy(self):
        logger.info("Application shutdown", extra={"event_id": L.UI.APP_SHUTDOWN})
        super().destroy()
