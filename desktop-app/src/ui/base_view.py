# src/ui/BaseFrame.py

import customtkinter as ctk

from src.core.logging_config import get_logger
from src.core.log_events import L

logger = get_logger(__name__)


class BaseFrame(ctk.CTkFrame):
    """
    BASE FRAME

    Purpose:
    - Acts as the common foundation for all content frames
    - Provides lifecycle hooks for visibility and animation
    - Keeps ApplicationShell free from frame-specific logic

    This class MUST remain lightweight.
    """
    def __init__(self, master, controller=None, **kwargs):
        # Enforce transparent background by default
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        self.controller = controller
        self._visible = False

        # Standard grid behavior for all content frames
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        logger.debug("%s initialized", self.__class__.__name__, extra={"event_id": L.VW.VIEW_CREATED})

    # ======================================================
    # Visibility Lifecycle (called by ApplicationShell)
    # ======================================================
    def show(self):
        """
        Called when the frame is brought into view.
        """
        if self._visible:
            return

        self._visible = True
        self.on_show()
        self.animate_in()

        logger.debug("%s shown", self.__class__.__name__, extra={"event_id": L.VW.VIEW_SHOWN})

    def hide(self):
        """
        Called when the frame is removed from view.
        """
        if not self._visible:
            return

        self._visible = False
        self.on_hide()
        self.animate_out()

        logger.debug("%s hidden", self.__class__.__name__, extra={"event_id": L.VW.VIEW_HIDDEN})

    # ======================================================
    # Hooks — override in child frames if needed
    # ======================================================
    def on_show(self):
        """
        Hook: frame became visible.
        Override in child class if needed.
        """
        pass

    def on_hide(self):
        """
        Hook: frame is being hidden.
        Override in child class if needed.
        """
        pass

    def animate_in(self):
        """
        Hook for future animations when frame appears.
        Safe no-op by default.
        """
        pass

    def animate_out(self):
        """
        Hook for future animations when frame disappears.
        Safe no-op by default.
        """
        pass

    # ======================================================
    # Optional data refresh hook
    # ======================================================
    def refresh_data(self):
        """
        Optional hook for updating frame data.
        Child frames may override.
        """
        pass
