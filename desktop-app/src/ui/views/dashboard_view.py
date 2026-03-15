import customtkinter as ctk
import tkinter as tk
from PIL import Image

# Assuming BaseFrame is in your project structure
from src.ui.base_view import BaseFrame

class HomeFrame(BaseFrame):
    page_name = "Home"
    
    # --- STYLE CONSTANTS ---
    BG_COLOR = "#0F172A"       # Deep Slate
    CARD_COLOR = "#1E293B"     # Lighter Slate
    ACCENT_BLUE = "#3B82F6"    # Electric Blue
    ACCENT_GREEN = "#10B981"   # Emerald
    TEXT_MAIN = "#F8FAFC"      # Off White
    TEXT_DIM = "#94A3B8"       # Muted Slate

    def __init__(self, master, controller=None, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.pulse_pos = 0 

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_dashboard()

    def _build_dashboard(self):
        container = ctk.CTkFrame(self, corner_radius=0, fg_color=self.BG_COLOR)
        container.grid(row=1, column=0, sticky="nsew")

        container.grid_columnconfigure((0, 1), weight=1)
        container.grid_rowconfigure(0, weight=0) # Header
        container.grid_rowconfigure(1, weight=0) # Active Project
        container.grid_rowconfigure(2, weight=1) # Stats Row

        # --- ROW 0: DASHBOARD HEADER ---
        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=30, pady=(30, 10))
        
        ctk.CTkLabel(header_frame, text="System Overview", 
                     font=("Segoe UI", 24, "bold"), text_color=self.TEXT_MAIN).pack(side="left")

        btn_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_container.pack(side="right")

        self.target_btn = ctk.CTkButton(
            btn_container, text="📡 Target: Online", fg_color="#064E3B", 
            hover_color="#065F46", text_color="#34D399", width=130, height=32, corner_radius=8
        )
        self.target_btn.pack(side="left", padx=10)

        self.update_btn = ctk.CTkButton(
            btn_container, text="⬆️ Update", fg_color=self.ACCENT_BLUE, 
            hover_color="#2563EB", width=100, height=32, corner_radius=8
        )
        self.update_btn.pack(side="left")

        # --- ROW 1: ACTIVE PROJECT (With Animation) ---
        active_project = self._card(container, "HARDWARE LINK STATUS", self.CARD_COLOR)
        active_project.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=30, pady=15)
        self._active_project_content(active_project)

        # --- ROW 2: SYSTEM METRICS ---
        system_load = self._card(container, "PERFORMANCE", self.CARD_COLOR)
        system_load.grid(row=2, column=0, sticky="nsew", padx=(30, 10), pady=(0, 30))
        self._system_load_content(system_load)

        recent_activity = self._card(container, "LOG ANALYTICS", self.CARD_COLOR)
        recent_activity.grid(row=2, column=1, sticky="nsew", padx=(10, 30), pady=(0, 30))
        self._recent_activity_content(recent_activity)

    def _card(self, master, title_text, color):
        card = ctk.CTkFrame(master, fg_color=color, corner_radius=16, border_width=1, border_color="#334155")
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title_text, font=("Segoe UI", 11, "bold"), 
                     text_color=self.TEXT_DIM).grid(row=0, column=0, sticky="w", padx=25, pady=(15, 0))
        return card

    def _active_project_content(self, card):
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=25, pady=(10, 20))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)

        # Info side
        info_side = ctk.CTkFrame(body, fg_color="transparent")
        info_side.grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(info_side, text="ESP32 Traffic Controller", 
                     font=("Segoe UI", 28, "bold"), text_color=self.TEXT_MAIN).pack(anchor="w")
        ctk.CTkLabel(info_side, text="v2.1.0 • Connected • Active Simulation", 
                     font=("Segoe UI", 13), text_color=self.ACCENT_BLUE).pack(anchor="w", pady=(0, 15))
        
        btns = ctk.CTkFrame(info_side, fg_color="transparent")
        btns.pack(anchor="w")
        ctk.CTkButton(btns, text="Open Workspace", width=140, height=34, fg_color=self.ACCENT_BLUE).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btns, text="Run Simulation", width=140, height=34, fg_color="#334155").pack(side="left")

        # Animation side
        self.canvas = tk.Canvas(body, bg=self.CARD_COLOR, highlightthickness=0, height=80)
        self.canvas.grid(row=0, column=1, sticky="nsew", padx=(20, 0))
        self._animate_data()

    def _animate_data(self):
        try:
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            if w <= 1:
                self.after(100, self._animate_data)
                return

            self.canvas.delete("all")
            y = h // 2
            
            # Draw Schematic
            self.canvas.create_rectangle(10, y-15, 40, y+15, outline=self.ACCENT_BLUE, width=2) # Laptop
            self.canvas.create_rectangle(w-40, y-15, w-10, y+15, outline=self.ACCENT_GREEN, width=2) # ESP32
            self.canvas.create_line(40, y, w-40, y, fill="#334155", width=1, dash=(2, 2))

            # Pulse
            self.pulse_pos += 4
            if self.pulse_pos > (w - 80): self.pulse_pos = 0
            
            curr_x = 40 + self.pulse_pos
            self.canvas.create_oval(curr_x-3, y-3, curr_x+3, y+3, fill=self.ACCENT_BLUE, outline="white")
            
            self.after(30, self._animate_data)
        except: pass

    def _system_load_content(self, card):
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=25, pady=(10, 20))
        self._metric_bar(body, "CPU USAGE", "34%", 0.34, self.ACCENT_BLUE)
        self._metric_bar(body, "MEMORY (RAM)", "1.2 / 8.0 GB", 0.15, self.ACCENT_GREEN)

    def _metric_bar(self, master, label, value, progress, color):
        row = ctk.CTkFrame(master, fg_color="transparent")
        row.pack(fill="x", pady=(5, 2))
        ctk.CTkLabel(row, text=label, font=("Segoe UI", 10, "bold"), text_color=self.TEXT_DIM).pack(side="left")
        ctk.CTkLabel(row, text=value, font=("Segoe UI", 10, "bold"), text_color=self.TEXT_MAIN).pack(side="right")
        bar = ctk.CTkProgressBar(master, progress_color=color, fg_color="#0F172A", height=6)
        bar.pack(fill="x", pady=(0, 10))
        bar.set(progress)

    def _recent_activity_content(self, card):
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=25, pady=(10, 20))
        logs = [("💾", "Main.cpp saved", "12:45 PM"), ("🧪", "Compiled: OK", "12:40 PM"), ("✨", "AI analysis done", "12:32 PM")]
        for icon, text, time in logs:
            log_item = ctk.CTkFrame(body, fg_color="transparent")
            log_item.pack(fill="x", pady=2)
            ctk.CTkLabel(log_item, text=f"{icon} {text}", font=("Segoe UI", 12), text_color=self.TEXT_MAIN).pack(side="left")
            ctk.CTkLabel(log_item, text=time, font=("Segoe UI", 11), text_color=self.TEXT_DIM).pack(side="right")