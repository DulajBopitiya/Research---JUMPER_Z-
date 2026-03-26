# JP_PLATFORM/src/ui/components/sidebar.py

import customtkinter as ctk
from PIL import Image

from src.core.event_bus import event_bus
from src.core.events import Events
from src.core.state import app_state
from src.core.state_keys import StateKeys
from src.core.logging_config import get_logger
from src.core.log_events import L
from src.utils.resource_path import resource_path 
from src.utils.image_utils import tint_image
from src.ui.theme import COLORS

ICON_PATH = "assets" 
SIDEBAR_WIDTH_EXPANDED = 180
SIDEBAR_WIDTH_COLLAPSED = 45
TOGGLE_BTN_SIZE = (24, 24)
NAV_BTN_SIZE = (20, 20)

logger = get_logger(__name__)

class SideBar(ctk.CTkFrame):
    """
    SideBar is a PURE UI component.

    Responsibilities:
    - Emit navigation intent
    - React to confirmed navigation
    - Manage its own visual layout (collapsed / expanded)

    Forbidden:
    - Deciding navigation success
    - Owning navigation truth
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=2, fg_color=(COLORS["sidebar_bg_light"], COLORS["sidebar_bg_dark"]),  **kwargs)
        
        self.buttons = {}               # Stores references to 'expanded' and 'icon' buttons

        # --- Grid Configuration ---
        self.grid_columnconfigure(0, weight=1)
        for i in range(10): 
            self.grid_rowconfigure(i, weight=0)
        self.grid_rowconfigure(6, weight=1)         # Flexible Spacer

        # --- Image/Assets Management ---
        self._initialize_assets()

        # --- Component Creation ---
        self._create_toggle_button()
        self._create_navigation_buttons()

        # Create the Active Indicator Bar (Thin Frame)
        self.active_indicator = ctk.CTkFrame(self, width=4, height=30, fg_color=COLORS["accent_blue"])                                              
        self.active_indicator.grid(row=0, column=0, padx=0, pady=0, sticky="nse")

        # --- Event Subscriptions (REACTION ONLY) ---
        event_bus.subscribe(Events.UI.SIDEBAR_STATE_CHANGED, self._apply_visual_state)
        event_bus.subscribe(Events.UI.NAVIGATION_ALLOWED, self._on_nav_confirmed)

        
        # --- Apply initial state ---
        collapsed = app_state.get(StateKeys.SIDEBAR_COLLAPSED, True)
        self._apply_visual_state(collapsed=collapsed)
        
        logger.debug("SideBar initialized.", event_id=L.UI.COMPONENT_INITIALIZED)

    # ---------------------------------------------------------
    # Asset handling
    # ---------------------------------------------------------
    def _initialize_assets(self):
        """Generates all tinted icons once for both light and dark modes."""
        try:
            # Navigation Icons
            items = ["Home", "Simulation", "Code Editor", "Measurements", "Data & Analysis", "Notifications", "Settings"]
            paths = {
                "Home": "icon_home.png",
                "Simulation": "icon_simulation.png",
                "Code Editor": "icon_code_editor.png",
                "Measurements": "icon_measure.png",
                "Data & Analysis": "icon_data.png",
                "Notifications": "icon_notification.png",
                "Settings": "icon_settings.png"
            }
            
            self.nav_images = {name: self._generate_dual_tint_icon(resource_path(f"{ICON_PATH}/{paths[name]}")) for name in items}
            
            # Toggle Icon
            self.toggle_icon = self._generate_dual_tint_icon(resource_path(f"{ICON_PATH}/icon_menu_open.png"), size=TOGGLE_BTN_SIZE)
            
            logger.debug("SideBar assets generated.", event_id=L.UI.ICON_LOADED)
        except Exception as e:
            logger.error(f"Asset generation failed: {e}", event_id=L.UI.ICON_LOAD_FAILED)     

    def _generate_dual_tint_icon(self, path: str, size=NAV_BTN_SIZE):
        """Creates a single CTkImage containing both light-mode and dark-mode versions."""
        original = Image.open(path)
        return ctk.CTkImage(
            light_image=tint_image(original.copy(), COLORS["text_dark"]),
            dark_image=tint_image(original.copy(), COLORS["text_light"]),
            size=size
        )  

    # ---------------------------------------------------------
    # UI construction
    # ---------------------------------------------------------
    def _create_toggle_button(self):
        self.toggle_button = ctk.CTkButton(
            self, text="", image=self.toggle_icon,
            width=40, height=40, 
            fg_color="transparent", 
            hover_color=(COLORS["hover_light"], COLORS["hover_dark"]),
            command=self._on_toggle_clicked,
            anchor="w"
        )
        self.toggle_button.grid(row=0, column=0, padx=20, pady=5, sticky="new")

    def _create_navigation_buttons(self):
        nav_items = [
            ("Home", 1), 
            ("Simulation", 2),
            ("Code Editor", 3),
            ("Measurements", 4), 
            ("Data & Analysis", 5), 
            ("Notifications", 8),   # Placed in row 8, below the spacer
            ("Settings", 9),        # Placed in row 9, below Notifications
        ]

        for name, row in nav_items:
            image_obj = self.nav_images.get(name)

            # Use tuples for colors so CTk handles the switch automatically
            common_kwargs = {
                "image": image_obj,
                "fg_color": "transparent",
                "hover_color": (COLORS["hover_light"], COLORS["hover_dark"]),
                "command": lambda n=name: self._on_nav_clicked(n)
            }

            # 1. Expanded Button (Visible when sidebar is wide)
            expanded_button = ctk.CTkButton(self, text=f" {name}", compound="left", anchor="w",
                                            text_color=(COLORS["text_dark"], COLORS["text_light"]), 
                                            **common_kwargs)
            
             # 2. Icon Button (Visible when sidebar is collapsed)
            icon_button = ctk.CTkButton(self, text="", width=35, height=35, **common_kwargs)

            # Place the expanded button initially (it will be hidden by the initial toggle)
            expanded_button.grid(row=row, column=0, padx=20, pady=(5, 5), sticky="ew")
            
            self.buttons[name] = {"expanded": expanded_button, "icon": icon_button, "row": row}

    # ---------------------------------------------------------
    # Intent emission
    # ---------------------------------------------------------
    def _on_toggle_clicked(self):
        event_bus.emit(Events.UI.SIDEBAR_TOGGLE_REQUESTED)

    def _on_nav_clicked(self, target: str):
        """
        Emits intent ONLY.
        No UI state change here.
        """
        event_bus.emit(Events.UI.NAVIGATION_REQUESTED, target=target)
        logger.info(f"Navigation requested: {target}", event_id=L.VW.BUTTON_CLICKED)
        
    # ---------------------------------------------------------
    # Reaction to confirmation
    # ---------------------------------------------------------
    def _on_nav_confirmed(self, target: str):
        """React ONLY to confirmed navigation from the AppController."""
        self.set_active_button(target)

    # ---------------------------------------------------------
    # Sidebar layout (UI-owned)
    # ---------------------------------------------------------
    def set_active_button(self, name):
        """Updates the foreground color and moves the indicator bar to show which button is active."""
        accent = COLORS["accent_blue"]

        for btn_name, refs in self.buttons.items():
            is_active = (btn_name == name)
            color = accent if is_active else "transparent"
            
            refs["expanded"].configure(fg_color=color)
            refs["icon"].configure(fg_color=color)
            
            if is_active:
                self.active_indicator.grid(row=refs["row"], column=0, padx=0, pady=8, sticky="nw")

    def _apply_visual_state(self, collapsed=False, *args, **kwargs):
        """Toggles the sidebar between expanded and collapsed states, keeping a single icon."""
        if collapsed:
            # --- ACTION: COLLAPSE Sidebar (Current state is Expanded) ---
            self.configure(width=SIDEBAR_WIDTH_COLLAPSED)
            self.toggle_button.configure(anchor="center") 
            self.toggle_button.grid(row=0, column=0, padx=5, pady=5, sticky="n") 
            
            for refs in self.buttons.values():
                refs["expanded"].grid_forget()
                refs["icon"].grid(row=refs["row"], column=0, padx=5, pady=(5, 5), sticky="n")
            
        else:
            # --- ACTION: EXPAND Sidebar (Current state is Collapsed) ---
            self.configure(width=SIDEBAR_WIDTH_EXPANDED)
            self.toggle_button.configure(anchor="w") 
            self.toggle_button.grid(row=0, column=0, padx=20, pady=0, sticky="w")
            
            for refs in self.buttons.values():
                refs["icon"].grid_forget()
                refs["expanded"].grid(row=refs["row"], column=0, padx=20, pady=(5, 5), sticky="ew")

        logger.info("Sidebar state applied: %s", "collapsed" if collapsed else "expanded", event_id=L.UI.SIDEBAR_TOGGLED)