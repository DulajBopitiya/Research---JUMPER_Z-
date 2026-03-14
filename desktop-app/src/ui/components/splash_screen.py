# src/ui/components/splash_screen.py

import customtkinter as ctk
from src.core.config import APP_NAME, ASSET_DIR

class SplashScreen(ctk.CTkToplevel):
    def __init__(self):
        super().__init__()
        
        # 1. Window Configuration (Borderless & Centered)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        width, height = 400, 250
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # 2. UI Elements
        self.label = ctk.CTkLabel(self, text=APP_NAME, font=("Roboto", 32, "bold"))
        self.label.pack(expand=True)
        
        self.status = ctk.CTkLabel(self, text="Initializing...", font=("Roboto", 12))
        self.status.pack(pady=20)
        
        # Force redraw so it shows up immediately
        self.update()

    def update_status(self, text: str):
        """Update the loading text (e.g., 'Loading Arduino CLI...')"""
        self.status.configure(text=text)
        self.update()
