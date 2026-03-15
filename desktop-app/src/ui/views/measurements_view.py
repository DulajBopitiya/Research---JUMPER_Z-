import customtkinter as ctk
import random
from datetime import datetime
from src.ui.base_view import BaseFrame
from src.utils.VirtualBreadboard import VirtualBreadboard

# Professional UX Palette
CLR_BG = "#0D1117"           # Deep canvas background
CLR_PANEL = "#161B22"        # Secondary sections
CLR_CARD = "#21262D"         # Individual cards/rows
CLR_BORDER = "#30363D"       # Subtle borders
CLR_ACCENT_A = "#10B981"     # Emerald (Primary)
CLR_ACCENT_B = "#3B82F6"     # Blue (Secondary)
CLR_TEXT_MAIN = "#F0F6FC"    # Primary text
CLR_TEXT_DIM = "#8B949E"     # Muted text

class MeasurementsFrame(BaseFrame):
    FRAME_NAME = "Measurements"

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.mapping_target = None  
        self.current_val = 0.000
        self.probe_coords = {"A": None, "B": None}
        self.badge_slots = {"A": None, "B": None}
        self.probe_nodes = {"A": None, "B": None} 
        self.after_id_count = 0
        self.zoom_scale = 1.0
        self.GRID_SIZE = 24

        # Layout Configuration
        self.grid_columnconfigure(0, weight=2) # Main Content (Breadboard)
        self.grid_columnconfigure(1, weight=0) # Right Sidebar
        self.grid_rowconfigure(0, weight=1)

        self._setup_virtual_breadboard()
        self._setup_control_sidebar()
        self._setup_data_visualizer()

        self._animate_link_loop()

    def _setup_virtual_breadboard(self):
        """Top Section: weight=3"""
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(0, weight=5) 
    
        self.bb_container = ctk.CTkFrame(
            self.main_content, 
            fg_color=CLR_PANEL, 
            corner_radius=8, 
            border_width=1, 
            border_color=CLR_BORDER
        )
        self.bb_container.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        
        # Header for Breadboard
        ctk.CTkLabel(
            self.bb_container, 
            text="◈ VIRTUAL BREADBOARD (LIVE)", 
            font=("Inter", 12, "bold"), 
            text_color=CLR_TEXT_DIM
        ).pack(anchor="w", padx=12, pady=(10, 5))

        # Canvas for the actual breadboard graphics
        self.canvas = ctk.CTkCanvas(
            self.bb_container, 
            bg="#08101D", 
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(expand=True, fill="both", padx=8, pady=(0, 8))

        # Initialize the External Renderer
        self.v_bb = VirtualBreadboard(self.canvas)

        # Bindings for interactive mapping
        self.canvas.bind("<Motion>", self._draw_ghost_probe)
        self.canvas.bind("<Button-1>", self._handle_canvas_click)

        # Override Configure to handle both Board and Probe redraws
        self.canvas.bind("<Configure>", lambda e: self._sync_render(), add="+")

    def _sync_render(self):
        """Master render orchestrator - Ensures probes are ALWAYS on top"""
        self.v_bb.zoom_scale = self.zoom_scale
        
        # 1. Clear everything for a fresh frame
        self.canvas.delete("all") 
        
        # 2. Draw the Breadboard first (Bottom Layer)
        self.v_bb._render_breadboard_asset() 
        
        # 3. Draw BOTH probes (Top Layer)
        # We iterate through our saved nodes. If a probe is 'stuck', we redraw it.
        for label in ["A", "B"]:
            node_id = self.probe_nodes.get(label)
            if node_id and node_id != "--":
                # Get the current pixel position of that node (handles zoom/resize)
                pos = self.v_bb.get_coords_of_node(node_id)
                if pos:
                    sx, sy = pos
                    color = CLR_ACCENT_A if label == "A" else CLR_ACCENT_B
                    
                    # Update coords for the link wire logic
                    self.probe_coords[label] = (sx, sy)
                    
                    # DRAW THE PROBE
                    self._render_probe_asset(sx, sy, color, f"stuck_{label}")

        # 4. Final Polish: Lift interaction layers to the very top
        self.canvas.tag_raise("link_line")
        self.canvas.tag_raise("spark")

    def _setup_control_sidebar(self):
        """Right Section: Instrument Controls"""
        self.sidebar = ctk.CTkFrame(
            self, 
            width=260, 
            fg_color=CLR_BG, 
            border_width=1, 
            border_color=CLR_BORDER,
            corner_radius=0
        )
        self.sidebar.grid(row=0, column=1, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Header
        ctk.CTkLabel(
            self.sidebar, 
            text="INSTRUMENT SETUP", 
            font=("Inter", 13, "bold"), 
            text_color=CLR_TEXT_MAIN
        ).pack(pady=(15, 10), padx=20, anchor="center")

        # Probe Mapping Group
        probe_f = self._create_sidebar_group("PROBE ATTACHMENTS")
        self._build_probe_ctrl(probe_f, "A", CLR_ACCENT_A)
        self._build_probe_ctrl(probe_f, "B", CLR_ACCENT_B)

        # Mode Selection
        mode_f = self._create_sidebar_group("MEASUREMENT MODE")
        self.mode_var = ctk.StringVar(value="VOLTAGE (V)")
        for m in ["VOLTAGE (V)", "CURRENT (I)", "RESISTANCE (Ω)"]:
            ctk.CTkRadioButton(
                mode_f, text=m, variable=self.mode_var, value=m, 
                font=("Inter", 11), fg_color=CLR_ACCENT_A,
                radiobutton_width=16, radiobutton_height=16
            ).pack(pady=4, anchor="w")

        # Action Button
        self.execute_btn = ctk.CTkButton(
            self.sidebar, text="CAPTURE DATA", height=42, 
            fg_color=CLR_ACCENT_A, hover_color="#0D9488", 
            text_color="#000", font=("Inter", 12, "bold"),
            command=self._mock_measure
        )
        self.execute_btn.pack(side="bottom", fill="x", padx=20, pady=20)

    # --- PROBE ENGINE & BADGE UI ---

    def _build_probe_ctrl(self, parent, label, color):
        """The New Badge-Enabled Probe Control"""
        f = ctk.CTkFrame(parent, fg_color=CLR_CARD, height=65, corner_radius=10, border_width=1, border_color=CLR_BORDER)
        f.pack(fill="x", pady=4)
        f.pack_propagate(False) 
        ctk.CTkFrame(f, width=3, fg_color=color).pack(side="left", padx=(10, 8), pady=12)
        
        txt_f = ctk.CTkFrame(f, fg_color="transparent")
        txt_f.pack(side="left", fill="y", pady=8)
        ctk.CTkLabel(txt_f, text=f"PROBE {label}", font=("Inter", 10, "bold"), text_color=CLR_TEXT_DIM).pack(anchor="w")

        self.badge_slots[label] = ctk.CTkFrame(txt_f, fg_color="transparent")
        self.badge_slots[label].pack(anchor="w")
        self._refresh_badge_ui(label, "--", color) # Initial state
        
        btn = ctk.CTkButton(f, text="MOUNT", width=60, height=28, fg_color=CLR_BG, hover_color=color,
                            text_color=CLR_TEXT_MAIN, font=("Inter", 10, "bold"), border_width=1, border_color=CLR_BORDER,
                            command=lambda l=label: self._start_mapping(l))
        btn.pack(side="right", padx=10)

    def _refresh_badge_ui(self, label, pin, color):
        """The Badge Engine: generates the silicon-style node indicator"""
        for child in self.badge_slots[label].winfo_children():
            child.destroy()

        if pin == "--":
            ctk.CTkLabel(self.badge_slots[label], text="--", font=("JetBrains Mono", 14, "bold"), text_color="#475569").pack(anchor="w")
        else:
            badge = ctk.CTkFrame(self.badge_slots[label], fg_color="#000", corner_radius=6, border_width=1, border_color=color)
            badge.pack(anchor="w", pady=(2, 0))
            ctk.CTkLabel(badge, text=pin, font=("JetBrains Mono", 11, "bold"), text_color=color).pack(padx=8, pady=2)

    # --- ANIMATION & PHYSICS ---

    def _animate_link_loop(self):
        """Calculates and draws the flowing link between probes"""
        self.canvas.delete("link_line")
        ca, cb = self.probe_coords["A"], self.probe_coords["B"]

        if ca and cb:
            offset = self.after_id_count % 8
            # Differential Path
            self.canvas.create_line(ca[0], ca[1], cb[0], cb[1], 
                                     fill="#1E293B", width=1, tags="link_line", 
                                     dash=(4, 4), dashoffset=offset)
            # Contact Points
            self.canvas.create_oval(ca[0]-3, ca[1]-3, ca[0]+3, ca[1]+3, fill=CLR_ACCENT_A, outline="", tags="link_line")
            self.canvas.create_oval(cb[0]-3, cb[1]-3, cb[0]+3, cb[1]+3, fill=CLR_ACCENT_B, outline="", tags="link_line")

        self.after_id_count += 1
        self.after(50, self._animate_link_loop)

    def _trigger_spark(self, x, y, color):
        """High-fidelity plasma expansion effect"""
        def animate(r, alpha):
            if r > 35: 
                self.canvas.delete("spark_fx")
                return
            # Create a hex string for fading (simulated)
            self.canvas.create_oval(x-r, y-r, x+r, y+r, outline=color, width=2, tags="spark_fx")
            self.after(15, lambda: [self.canvas.delete("spark_fx"), animate(r + 4, alpha)])
        animate(4, 1.0)

    def _start_telemetry_jitter(self):
        """Simulates real-world signal fluctuation"""
        jitter = random.uniform(-0.002, 0.002)
        display_val = max(0, self.current_val + jitter)
        if self.current_val > 0:
            self.val_label.configure(text=f"{display_val:.3f}")
        self.after(120, self._start_telemetry_jitter)

    # --- CANVAS RENDERING ---

    def _render_probe_asset(self, x, y, color, tag):
        """Ultra-premium Industrial Probe with specular highlights and mechanical depth"""
        # 1. THE NEEDLE (Surgical Steel Look)
        # Main taper
        self.canvas.create_polygon(x, y, x-1.5, y-18, x+1.5, y-18, fill="#CBD5E1", tags=tag)
        # Center shine on needle
        self.canvas.create_line(x, y-2, x, y-18, fill="#F8FAFC", width=1, tags=tag)
        
        # 2. THE HAND-GUARD (Base of the handle)
        self.canvas.create_rectangle(x-8, y-18, x+8, y-22, fill="#0F172A", outline="#000", width=1, tags=tag)
        
        # 3. THE MAIN CHASSIS (Deep Matte Body)
        # Main body shadow
        self.canvas.create_rectangle(x-7, y-22, x+7, y-75, fill="#1E293B", outline="#000", tags=tag)
        # Highlight on the left to give 3D rounded feel
        self.canvas.create_line(x-4, y-23, x-4, y-74, fill="#334155", width=2, tags=tag)
        
        # 4. PREMIUM KNURLING (Textured Grip)
        for i in range(y-30, y-55, 5):
            self.canvas.create_line(x-5, i, x+5, i, fill="#0F172A", width=1, tags=tag)
            self.canvas.create_line(x-5, i+1, x+5, i+1, fill="#334155", width=1, tags=tag)

        # 5. ILLUMINATED ID RING (Recessed and Glowing)
        # Darker border for depth
        self.canvas.create_rectangle(x-7, y-58, x+7, y-65, fill="#000", outline="", tags=tag)
        # The core color
        self.canvas.create_rectangle(x-7, y-60, x+7, y-63, fill=color, outline="", tags=tag)
        
        # 6. TOP HEX CAP (Mechanical transition)
        self.canvas.create_polygon(x-7, y-75, x+7, y-75, x+5, y-82, x-5, y-82, fill="#0F172A", outline="#000", tags=tag)

        # 7. HIGH-FIDELITY LEAD WIRE
        # Secondary shadow line for thickness
        self.canvas.create_line(x, y-82, x+17, y-107, x+42, y-122, fill="#000", width=4, smooth=True, tags=tag)
        # Main lead color
        self.canvas.create_line(x, y-82, x+15, y-105, x+40, y-120, fill=color, width=2, smooth=True, capstyle="round", tags=tag)

    def _start_mapping(self, label):
        self.mapping_target = label
        self.canvas.configure(cursor="none")

    def _draw_ghost_probe(self, event):
        self.canvas.delete("ghost")
        if self.mapping_target:
            sx = round(event.x / self.GRID_SIZE) * self.GRID_SIZE
            sy = round(event.y / self.GRID_SIZE) * self.GRID_SIZE
            c = CLR_ACCENT_A if self.mapping_target == "A" else CLR_ACCENT_B
            self.canvas.create_oval(sx-8, sy-8, sx+8, sy+8, outline=c, width=1, dash=(2,2), tags="ghost")
            self._render_probe_asset(sx, sy, c, "ghost")

    def _handle_canvas_click(self, event):
        if self.mapping_target:
            node_data = self.v_bb.get_node_at(event.x, event.y)
            
            if node_data:
                sx, sy, node_id = node_data
                color = CLR_ACCENT_A if self.mapping_target == "A" else CLR_ACCENT_B
                
                # --- THE LOGIC HANDSHAKE ---
                # Save the node name so sync_render knows WHERE to draw it
                self.probe_nodes[self.mapping_target] = node_id
                # Save the pixel coords so animate_link knows WHERE to draw the wire
                self.probe_coords[self.mapping_target] = (sx, sy)
                
                # Visual/UI updates
                self._refresh_badge_ui(self.mapping_target, node_id, color)
                self._trigger_spark(sx, sy, color)
                
                # Reset mapping state
                self.mapping_target = None
                self.canvas.configure(cursor="arrow")
                self.canvas.delete("ghost")
                
                # --- THE FIX ---
                # Now that state is saved, trigger a full re-render.
                # Since probe_nodes[label] is now NOT None, _sync_render will draw it.
                self._sync_render()

    #===================================================

    def _setup_data_visualizer(self):
        """Bottom Section: weight=2"""
        self.hub = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.hub.grid(row=1, column=0, sticky="nsew")
        self.hub.grid_columnconfigure(0, weight=2)
        self.hub.grid_columnconfigure(1, weight=1)

        # Telemetry Log
        self.log_f = ctk.CTkFrame(self.hub, fg_color=CLR_PANEL, corner_radius=8, border_width=1, border_color=CLR_BORDER)
        self.log_f.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._create_log_table()

        # Analytics Dash
        self.vitals_f = ctk.CTkFrame(self.hub, fg_color=CLR_PANEL, corner_radius=8, border_width=1, border_color=CLR_BORDER)
        self.vitals_f.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._create_vitals_dashboard()

    # --- Helper Builders ---

    def _create_sidebar_group(self, title):
        f = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f, text=title, font=("Inter", 11, "bold"), text_color=CLR_TEXT_DIM).pack(anchor="w", pady=(0, 5))
        return f

    def _build_probe_indicator(self, parent, label, node, color):
        f = ctk.CTkFrame(parent, fg_color=CLR_CARD, height=35, corner_radius=6)
        f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=f"PROBE {label}", font=("Inter", 10), text_color=CLR_TEXT_DIM).pack(side="left", padx=12)
        ctk.CTkLabel(f, text=node, font=("JetBrains Mono", 11, "bold"), text_color=color).pack(side="right", padx=12)

    def _create_log_table(self):
        ctk.CTkLabel(self.log_f, text="◈ TELEMETRY LOG", font=("Inter", 11, "bold"), text_color=CLR_TEXT_DIM).pack(anchor="w", padx=15, pady=8)
        self.scroll = ctk.CTkScrollableFrame(self.log_f, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=4, pady=4)
        
        header = ctk.CTkFrame(self.scroll, fg_color=CLR_CARD, height=26, corner_radius=4)
        header.pack(fill="x", pady=(0, 6))
        for txt in ["TIME", "NODES", "VALUE"]:
            ctk.CTkLabel(header, text=txt, font=("Inter", 8, "bold"), text_color=CLR_TEXT_DIM, width=70).pack(side="left", padx=10)

    def _create_vitals_dashboard(self):
        ctk.CTkLabel(self.vitals_f, text="◈ ANALYSIS", font=("Inter", 11, "bold"), text_color=CLR_TEXT_DIM).pack(pady=8)
        stats = [("PEAK AVG", "4.992V", CLR_ACCENT_A), ("UPTIME", "00:14:22", CLR_ACCENT_B)]
        for label, val, color in stats:
            card = ctk.CTkFrame(self.vitals_f, fg_color=CLR_CARD, corner_radius=6)
            card.pack(fill="x", padx=15, pady=4)
            # Replaced .place() with .pack() for stability
            ctk.CTkLabel(card, text=label, font=("Inter", 8, "bold"), text_color=CLR_TEXT_DIM).pack(anchor="w", padx=10, pady=(4, 0))
            ctk.CTkLabel(card, text=val, font=("JetBrains Mono", 16, "bold"), text_color=color).pack(anchor="w", padx=10, pady=(0, 4))

    def _mock_measure(self):
        print(f"Executing {self.mode_var.get()} at {datetime.now()}")