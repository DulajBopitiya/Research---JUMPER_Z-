import customtkinter as ctk
from datetime import datetime

UI_FONT = ("Segoe UI", 12)
UI_FONT_SMALL = ("Segoe UI", 11)
UI_FONT_BOLD = ("Segoe UI", 12, "bold")

MONO_FONT = ("Consolas", 22, "bold")


class MetricCard(ctk.CTkFrame):
    def __init__(self, master, title, unit):
        super().__init__(
            master,
            corner_radius=12,
            fg_color=("gray15", "gray20")
        )

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text=title,
            font=UI_FONT_SMALL,
            text_color=("gray70", "gray60"),
            anchor="w"
        ).grid(row=0, column=0, padx=12, pady=(8, 0), sticky="w")

        self.value = ctk.CTkLabel(
            self,
            text="--",
            font=MONO_FONT,
            anchor="w"
        )
        self.value.grid(row=1, column=0, padx=12, sticky="w")

        ctk.CTkLabel(
            self,
            text=unit,
            font=UI_FONT_SMALL,
            text_color=("gray60", "gray50"),
            anchor="w"
        ).grid(row=2, column=0, padx=12, sticky="w")

        self.status = ctk.CTkLabel(
            self,
            text="—",
            font=UI_FONT_SMALL,
            anchor="w"
        )
        self.status.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="w")

    def update(self, value, status="OK", color="green"):
        self.value.configure(text=str(value))
        self.status.configure(text=status, text_color=color)
