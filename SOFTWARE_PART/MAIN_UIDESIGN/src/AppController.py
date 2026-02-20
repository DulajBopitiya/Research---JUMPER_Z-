

import customtkinter as ctk

# --- Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def _init_(self):
        # super()._init_()
        
        # Window setup
        self.title("Blank Jumperless Platform Window")
        self.geometry("800x600")