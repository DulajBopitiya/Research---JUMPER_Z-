# src/ui/content/SettingsFrame.py

import customtkinter as ctk

class SettingsFrame(ctk.CTkFrame):
    """
    Frame dedicated to managing application-wide settings such as
    theme, language, connection parameters, and user preferences.
    """
    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, **kwargs)

        self.controller = controller
        
        # --- Configure Grid Layout ---
        self.grid_rowconfigure(4, weight=1)    # Spacer row to push content up
        self.grid_columnconfigure(0, weight=1) # Main column (expands horizontally)
        
        # --- Content Widgets ---
        
        self.header_label = ctk.CTkLabel(self, 
                                         text="Application Settings", 
                                         font=ctk.CTkFont(size=24, weight="bold"))
        self.header_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nw")

        # 1. Appearance/Theme Section
        self.appearance_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.appearance_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.appearance_frame.grid_columnconfigure(1, weight=1) # Push content to the right
        
        self.theme_label = ctk.CTkLabel(self.appearance_frame, text="Appearance Mode:")
        self.theme_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.theme_optionmenu = ctk.CTkOptionMenu(self.appearance_frame,
                                                  values=["System", "Dark", "Light"],
                                                  command=self.change_appearance_mode_event)
        self.theme_optionmenu.grid(row=0, column=2, padx=10, pady=5, sticky="e")
        self.theme_optionmenu.set(ctk.get_appearance_mode()) # Set initial value
        

        # 2. Connection Settings (Placeholder)
        self.conn_label = ctk.CTkLabel(self, text="Connection Settings: [Placeholder for input fields]", anchor="w")
        self.conn_label.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Set the background color for the main frame
        self.configure(fg_color=("gray95", "gray10")) 

    def change_appearance_mode_event(self, new_appearance_mode: str):
        """Updates the CustomTkinter theme."""
        ctk.set_appearance_mode(new_appearance_mode)
        print(f"Theme changed to: {new_appearance_mode}")

    def refresh_data(self):
        """Method to call when the frame is brought to the front."""
        print("SettingsFrame data refreshed.")