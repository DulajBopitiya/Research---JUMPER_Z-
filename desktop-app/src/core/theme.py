# src/core/theme.py

import customtkinter as ctk
from src.core.config import DEFAULT_APPEARANCE_MODE, DEFAULT_THEME
from src.core.logging_config import get_logger
from src.core.log_events import L

logger = get_logger(__name__)

# ================================================================
#                           COLOR PALETTE
# ================================================================
COLORS = {
    "primary": "#1E88E5",         # !!!!! ALL SAMPLES PLEASE CHANGE !!!!!
    "secondary": "#3949AB",
    "background_light": "#FFFFFF",
    "background_dark": "#0A0A0A",
    "accent": "#4F8CFF",
    "error": "#E53935",
    "warning": "#FB8C00",
    "success": "#43A047",

    # Surfaces
    "surface":        "#1A1D24",
    "surface_hover":  "#232733",
    "text_primary":   "#E8EAF0",

    "frame_bg_light": "#F2F2F2",
    "frame_bg_dark": "#1A1A1A",
    "sidebar_bg_light": "#EBEBEB",
    "sidebar_bg_dark": "#1A1A1A",
    "text_light": "#E0E0E0",   # Used for icons/text in Dark Mode
    "text_dark": "#212121",    # Used for icons/text in Light Mode
    "accent_blue": "#127CC1",
    "hover_light": "#E5E5E5",
    "hover_dark": "#2D2D2D",

    "border": "#2E3440",

}

THEME_COLORS = {
    "light": {
        "sidebar_bg": "gray90",
        "button_active": "gray80",
        "button_inactive": "gray25",
        "indicator": "#007ACC",
        "icon_text": "#000000"
    },
    "dark": {
        "sidebar_bg": "gray20",
        "button_active": "gray75",
        "button_inactive": "gray25",
        "indicator": "#00BFFF",
        "icon_text": "#FFFFFF"
    }
}
# ================================================================
#                     THEME APPLICATION FUNCTION
# ================================================================

def apply_theme():
    """
    Apply global CustomTkinter theme using config.py constants.
    Robust: handles errors and falls back safely.
    """
    # --- Appearance Mode ---
    try:
        ctk.set_appearance_mode(DEFAULT_APPEARANCE_MODE)
    except Exception as e:
        logger.warning("Failed to set appearance mode '%s': %s. Falling back to 'system'.", 
                       DEFAULT_APPEARANCE_MODE, e, extra={"event_id": L.UI.APP_THEME_WARNING})
        try:
            ctk.set_appearance_mode("system")
        except Exception:
            logger.error("Failed to apply fallback appearance mode 'system'.",
                         extra={"event_id": L.UI.APP_THEME_ERROR})

    # --- Color Theme ---
    try:
        ctk.set_default_color_theme(DEFAULT_THEME)
    except Exception as e:
        logger.warning("Failed to load CTk theme '%s': %s. Using CTk default.",
                       DEFAULT_THEME, e, extra={"event_id": L.UI.APP_THEME_ERROR})
