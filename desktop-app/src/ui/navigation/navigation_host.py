# src/ui/navigation/navigation_host.py

import customtkinter as ctk

from src.core.logging_config import get_logger
from src.core.log_events import L
from src.ui.navigation.view_registry import view_registry

logger = get_logger(__name__)

class NavigationHost(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self._views = {}
        self._active_view = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def show(self, name: str):

        # Lazy create
        if name not in self._views:
            view = view_registry.create(name, self)
            view.grid(row=0, column=0, sticky="nsew")
            view.grid_remove()
            self._views[name] = view

        next_view = self._views[name]

        # hide previous
        if self._active_view:
            try:
                self._active_view.on_hide()
            except Exception:
                pass
            self._active_view.grid_remove()

        # show new
        next_view.grid()
        next_view.tkraise()

        try:
            next_view.on_show()
        except Exception:
            pass

        self._active_view = next_view

        logger.info("Frame shown: %s", name, extra={"event_id": L.VW.VIEW_SHOWN})