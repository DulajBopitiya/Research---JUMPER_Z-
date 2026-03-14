# src/ui/content/NotificationsFrame.py

import customtkinter as ctk

class NotificationsFrame(ctk.CTkFrame):
    """
    Frame dedicated to displaying system alerts, warnings, errors, and 
    general informational messages in a scrollable list format.
    """
    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, **kwargs)

        self.controller = controller
        
        # --- Configure Grid Layout ---
        self.grid_rowconfigure(1, weight=1)    # Notification list area (expands vertically)
        self.grid_columnconfigure(0, weight=1) # Main column (expands horizontally)
        
        # --- Content Widgets ---
        
        self.header_label = ctk.CTkLabel(self, 
                                         text="System Notifications & Alerts", 
                                         font=ctk.CTkFont(size=24, weight="bold"))
        self.header_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nw")

        # 1. Scrollable Frame for Notification List
        self.notification_list_frame = ctk.CTkScrollableFrame(self, 
                                                              label_text="Recent Messages",
                                                              label_font=ctk.CTkFont(weight="bold"))
        self.notification_list_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # Add a few placeholder items to show how the list works
        self.notification_list_frame.grid_columnconfigure(0, weight=1)
        
        self.placeholder_note1 = ctk.CTkLabel(self.notification_list_frame, 
                                              text="[INFO] 12:45 PM: New data set 'Run 2025-11-08' is complete.", 
                                              anchor="w", justify="left")
        self.placeholder_note1.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        self.placeholder_note2 = ctk.CTkLabel(self.notification_list_frame, 
                                              text="[WARNING] 12:01 PM: Connection interrupted. Data saved locally.", 
                                              anchor="w", justify="left", text_color="orange")
        self.placeholder_note2.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        # Set the background color for the main frame
        self.configure(fg_color=("gray95", "gray10")) 

    def refresh_data(self):
        """Method to call when the frame is brought to the front."""
        print("NotificationsFrame data refreshed. (Ready to load alert history)")