# src/ui/content/SimulationFrame.py

import threading

import customtkinter as ctk
from PIL import Image

from src.ui.base_view import BaseFrame
#from src.ui.windows.oscilloscope.Master import launch_oscilloscope
from src.logic.wokwi_handler import WokwiHandler
from src.utils.resource_path import resource_path
from src.core.logging_config import get_logger
from src.utils.icon_card_button import IconCardButton

logger = get_logger(__name__)


class SimulationFrame(BaseFrame):
    # --- STYLE CONSTANTS ---
    BG_COLOR = "#0F172A"
    CARD_COLOR = "#1E293B"
    ACCENT_BLUE = "#3B82F6"
    TEXT_MAIN = "#F8FAFC"
    TEXT_DIM = "#94A3B8"

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color=self.BG_COLOR)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._create_ui()

    # ==================================================
    # UI LAYOUT
    # ==================================================
    def _create_ui(self):
        sim_container = ctk.CTkFrame(self, fg_color="transparent")
        sim_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        sim_container.grid_columnconfigure(0, weight=1)
        sim_container.grid_columnconfigure(1, weight=2)
        sim_container.grid_rowconfigure(0, weight=1)

        # ---------- LEFT PANEL ----------
        controls_frame = ctk.CTkFrame(
            sim_container,
            fg_color=self.CARD_COLOR,
            corner_radius=16,
            border_width=1,
            border_color="#334155"
        )
        controls_frame.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        controls_frame.grid_columnconfigure(0, weight=1)

        header_box = ctk.CTkFrame(controls_frame, fg_color="transparent")
        header_box.grid(row=0, column=0, padx=24, pady=(25, 15), sticky="w")

        ctk.CTkLabel(
            header_box,
            text="SIMULATION",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.ACCENT_BLUE
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_box,
            text="Hardware Controls",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.TEXT_MAIN
        ).pack(anchor="w")

        # Buttons
        IconCardButton(
            master=controls_frame,
            title="Oscilloscope",
            subtitle="Real-time signal analysis",
            icon_path="assets/scope_icon.png",
            command=self._open_osc_window
        ).grid(row=1, column=0, padx=20, pady=8, sticky="ew")

        IconCardButton(
            master=controls_frame,
            title="Function Generator",
            subtitle="Waveform ready for ESP32",
            icon_path="assets/fgen_icon.png",
            command=self._open_fngen_window
        ).grid(row=2, column=0, padx=20, pady=8, sticky="ew")

        controls_frame.grid_rowconfigure(3, weight=1)

        globe_icon = None
        try:
            globe_icon = ctk.CTkImage(
                Image.open(resource_path("assets/globe_icon.png")),
                size=(18, 18)
            )
        except Exception as e:
            logger.error(e)

        ctk.CTkButton(
            controls_frame,
            text="WOKWI Official Site",
            image=globe_icon,
            compound="right",
            command=self._open_wokwi,
            height=38,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=4, column=0, padx=20, pady=25)

        self.sync_button = ctk.CTkButton(
            controls_frame,
            text="SYNC SIMULATION",
            height=38,
            corner_radius=10,
            fg_color="#16A34A",
            hover_color="#22C55E",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._sync_wokwi
        )
        self.sync_button.grid(row=5, column=0, padx=20, pady=(0, 10))

        self.wokwi_url_entry = ctk.CTkEntry(
            controls_frame,
            placeholder_text="Paste Wokwi project URL",
            font=("Consolas", 12),
            fg_color="#334155",
        )
        self.wokwi_url_entry.grid(row=6, column=0, padx=20, pady=(0, 15), sticky="ew")

        self.sync_progress = ctk.CTkProgressBar(
            controls_frame,
            height=6,
            corner_radius=6,
            progress_color="#22C55E",
            fg_color="#1E293B"
        )
        self.sync_progress.set(0)
        self.sync_progress.grid(row=7, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.sync_progress.grid_remove()

        self.cancel_sync = False

        self.cancel_button = ctk.CTkButton(
            controls_frame,
            text="CANCEL SYNC",
            height=34,
            corner_radius=10,
            fg_color="#DC2626",
            hover_color="#EF4444",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._cancel_sync
        )
        self.cancel_button.grid(row=8, column=0, padx=20, pady=(0, 20))
        self.cancel_button.grid_remove()


        # ---------- RIGHT PANEL ----------
        connections_container = ctk.CTkFrame(
            sim_container,
            fg_color=self.CARD_COLOR,
            corner_radius=16,
            border_width=1,
            border_color="#334155"
        )
        connections_container.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        connections_container.grid_columnconfigure(0, weight=1)
        connections_container.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            connections_container,
            text="CONNECTION SCHEMATIC",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.TEXT_DIM
        ).grid(row=0, column=0, padx=25, pady=(20, 10), sticky="w")

        self.connections_display = ctk.CTkTextbox(
            connections_container,
            wrap="word",
            corner_radius=12,
            fg_color="#0F172A",
            text_color="#10B981",
            font=("Consolas", 13),
            border_width=1,
            border_color="#1E293B"
        )

        self.connections_display.insert(
            "end",
            "> WOKWI SIMULATION SYNC GUIDE\n"
            "> ---------------------------\n"
            "> 1. Open your circuit in Wokwi\n"
            "> 2. Ensure a breadboard (bb1) is used\n"
            "> 3. Copy the project URL\n"
            "> 4. Paste the URL on the left\n"
            "> 5. Click SYNC SIMULATION\n\n"
            "> Status messages will appear below.\n"
        )
        self.connections_display.configure(state="disabled")
        self.connections_display.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")

    # ==================================================
    # BUTTON ACTIONS
    # ==================================================
    def _open_osc_window(self):
        pass
        #if hasattr(self, "_osc_win") and self._osc_win.winfo_exists():
           # self._osc_win.lift()
        #else:
            #self._osc_win = launch_oscilloscope(self.master)

    def _open_fngen_window(self):
        pass

    def _open_wokwi(self):
        self._wokwi = getattr(self, "_wokwi", WokwiHandler())
        self._wokwi._open_wokwi()

    def _cancel_sync(self):
        self.cancel_sync = True
        self._append_log("Sync cancellation requested", "WARN")

    # ==================================================
    # BACKGROUND SYNC (NO UI BLOCKING)
    # ==================================================
    def _sync_wokwi(self):
        self._wokwi = getattr(self, "_wokwi", WokwiHandler())

        url = ""
        if hasattr(self, "wokwi_url_entry"):
            url = self.wokwi_url_entry.get().strip()

        # UI feedback (main thread)
        self._set_sync_ui_state(True)
        self._append_log("SYNC STARTED...")

        threading.Thread(
            target=self._sync_worker,
            args=(url,),
            daemon=True
        ).start()

    def _sync_worker(self, url):
        MAX_RETRIES = 3

        for attempt in range(1, MAX_RETRIES + 1):
            if self.cancel_sync:
                self.after(0, lambda: self._on_sync_error("Sync cancelled by user"))
                return
            
        try:
            data = self._wokwi.sync(
                project_url=url if url else None,
                send_to_board=True
            )
            # UI update must happen on main thread
            self.after(0, lambda d=data: self._on_sync_success(d))
            return
        
        except Exception as e:
            error_msg = str(e) 

            if attempt < MAX_RETRIES:
                self.after(0, lambda a=attempt: self._append_log(
                    f"Retrying sync ({a}/{MAX_RETRIES})...",
                    "WARN"
                    ) 
                )
            else:
                self.after(0, lambda msg=error_msg: self._on_sync_error(msg))

    def _on_sync_success(self, data):
        self._display_sync_result(data)
        self._append_log("SYNC COMPLETED SUCCESSFULLY")
        self._set_sync_ui_state(False)

    def _on_sync_error(self, error_msg):
        self._append_log(error_msg, "ERROR")
        self._set_sync_ui_state(False)

    # ==================================================
    # UI HELPERS
    # ==================================================
    def _set_sync_ui_state(self, syncing: bool):
        if syncing:
            self.cancel_sync = False
            self.sync_progress.grid()
            self.sync_progress.start()
            self.cancel_button.grid()
        else:
            self.sync_progress.stop()
            self.sync_progress.grid_remove()
            self.cancel_button.grid_remove()

        #self.sync_button.configure(state="disabled" if syncing else "normal")
        #self.configure(cursor="watch" if syncing else "")

    def _append_log(self, text, level="INFO"):
        colors = {
            "INFO": "#10B981",
            "WARN": "#F59E0B",
            "ERROR": "#EF4444"
        }

        self.connections_display.configure(state="normal")
        self.connections_display.insert("end", f"\n[{level}] {text}", level)
        self.connections_display.tag_config(level, foreground=colors[level])
        #self.connections_display.see("end")
        self.connections_display.configure(state="disabled")

    def _display_sync_result(self, data):
        self.connections_display.configure(state="normal")
        self.connections_display.delete("1.0", "end")
        self.connections_display.insert("end", data.get("diagram_text", "No data received"))
        self.connections_display.configure(state="disabled")


# https://wokwi.com/projects/456507397400115201