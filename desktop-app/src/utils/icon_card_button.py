import customtkinter as ctk
from PIL import Image, ImageTk
from src.utils.resource_path import resource_path

CARD_BG = ("#f0f0f0", "#1a1a1a")  # light and dark
CARD_HOVER_BG = ("#0078D7", "#0050a0")  # hover blue
ICON_SIZE = (36, 36)
TITLE_FONT = ("Segoe UI", 16, "bold")
SUBTITLE_FONT = ("Segoe UI", 13)
TITLE_COLOR = ("#000000", "#FFFFFF")
TITLE_HOVER_COLOR = ("#FFFFFF", "#FFFFFF")

class IconCardButton(ctk.CTkFrame):
    def __init__(self, master, title, subtitle, icon_path, command=None, **kwargs):
        super().__init__(master, fg_color=CARD_BG, corner_radius=12, **kwargs)
        self.command = command
        self.normal_bg = CARD_BG
        self.hover_bg = CARD_HOVER_BG
        self.normal_title_color = TITLE_COLOR
        self.hover_title_color = TITLE_HOVER_COLOR
        self.configure(cursor="hand2")

        # --- Load Icon ---
        try:
            img_data = Image.open(resource_path(icon_path))
            self.icon = ctk.CTkImage(
                light_image=img_data, 
                dark_image=img_data, 
                size=ICON_SIZE
            )
        except Exception as e:
            print(f"[ERROR] Failed to load icon: {e}")
            self.icon = None

        # --- Layout ---
        self.grid_rowconfigure(0, weight=0)

        # Icon label
        self.icon_label = ctk.CTkLabel(self, image=self.icon, text="")
        self.icon_label.grid(row=0, column=0, rowspan=2, padx=16, pady=(0, 0), sticky="w")

        # Title
        self.title_label = ctk.CTkLabel(self, text=title, font=TITLE_FONT, anchor="sw")
        self.title_label.grid(row=0, column=1, sticky="w", padx=(0,16), pady=(5, 2))

        # Subtitle
        self.subtitle_label = ctk.CTkLabel(self, text=subtitle, font=SUBTITLE_FONT, anchor="nw", text_color="#888888")
        self.subtitle_label.grid(row=1, column=1, sticky="w", padx=(0,16), pady=(2, 0))

        # --- Hover Bindings ---
        for widget in (self, self.icon_label, self.title_label, self.subtitle_label):
            widget.bind("<Enter>", self._on_hover)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)  # CLICK binding

    def _on_hover(self, event=None):
        self.configure(fg_color=self.hover_bg)
        self.title_label.configure(text_color=self.hover_title_color)
        self.subtitle_label.configure(text_color=self.hover_title_color)

    def _on_leave(self, event=None):
        self.configure(fg_color=self.normal_bg)
        self.title_label.configure(text_color=self.normal_title_color)
        self.subtitle_label.configure(text_color="#888888")

    def _on_click(self, event=None):
        if self.command:
            self.command()  # Trigger the assigned callback
