# JP_PLATFORM/src/utils/VirtualBreadboard.py

class VirtualBreadboard:
    """
    Pure renderer for a virtual breadboard.
    - No window ownership
    - No event bindings
    - Zoom is externally controlled (frame-owned)
    """

    def __init__(self, canvas):
        self.canvas = canvas

        # External state (set by parent frame)
        self.zoom_scale = 1.0

        # Geometry
        self.X_GAP = 24
        self.Y_GAP = 24
        self.PADDING = 60
        self.SEGMENT_GAP = 18

        # Refined engineering palette
        self.COLORS = {
            "bg": "#0a0a0b",                                            
            "board_body": "#333B3D",   
            "board_rim": "#2d2d35",     
            "hole_pit": "#08080a",     
            "hole_rim": "#6E6E86",      
            "rail_red": "#ff2d55",      
            "rail_blue": "#00f0ff",     
            "text_gold": "#ffcc00",     
            "text_silver": "#b5b5bd",   
            "divider_pit": "#0f0f12"       
        }

    # ==========================================================
    # PUBLIC API
    # ==========================================================

    def _calculate_dimensions(self):
        xs, ys = self.X_GAP * self.zoom_scale, self.Y_GAP * self.zoom_scale
        w, h = (29 * xs), 18 * ys 
        return w + (self.PADDING * 2 * self.zoom_scale), h + (self.PADDING * 2 * self.zoom_scale)

    def _render_breadboard_asset(self):
        self.canvas.delete("all")
        board_w, board_h = self._calculate_dimensions()
        x_mid, y_mid = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        x1, y1 = x_mid - (board_w / 2), y_mid - (board_h / 2)
        x2, y2 = x_mid + (board_w / 2), y_mid + (board_h / 2)
        
        # 1. OUTER CHASSIS
        # Shadow glow
        self.canvas.create_rectangle(x1-4, y1-4, x2+4, y2+4, outline="#1a1a20", width=1)
        # Main Board
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=self.COLORS["board_body"], 
                                     outline=self.COLORS["board_rim"], width=2)

        # 2. CENTER CHANNEL
        ys = self.Y_GAP * self.zoom_scale
        self.canvas.create_rectangle(x1+8, y_mid-ys/3, x2-8, y_mid+ys/3, 
                                     fill=self.COLORS["divider_pit"], outline="#222")
        self.canvas.create_text(x_mid, y_mid, text="CENTRAL DIVIDER", 
                               fill=self.COLORS["text_silver"], font=("Orbitron", int(8*self.zoom_scale), "bold"))

        # 3. DRAW GRID
        grid_x = x1 + (self.PADDING * self.zoom_scale)
        self._draw_grid_block(grid_x, y_mid - (1.6 * ys), "ABCDE", x1, x2, direction=-1)
        self._draw_grid_block(grid_x, y_mid + (1.6 * ys), "FGHIJ", x1, x2, direction=1)

    def _draw_pro_hole(self, cx, cy, accent=None):
        """Ultra-identifiable 3D recessed socket."""
        r = 5.5 * self.zoom_scale
        # Main socket area
        self.canvas.create_rectangle(cx-r, cy-r, cx+r, cy+r, 
                                     fill=self.COLORS["hole_pit"], 
                                     outline=accent if accent else self.COLORS["hole_rim"], 
                                     width=1)
        # Tactical Bottom Rim (Identification Glint)
        if not accent:
            self.canvas.create_line(cx-r+1, cy+r, cx+r, cy+r, fill="#444")
            self.canvas.create_line(cx+r, cy-r+1, cx+r, cy+r, fill="#444")

    def _draw_grid_block(self, x_start, y_base, labels, bx1, bx2, direction):
        xs, ys = self.X_GAP * self.zoom_scale, self.Y_GAP * self.zoom_scale
        lbls = labels[::-1] if direction == -1 else labels
        
        for row_idx, char in enumerate(lbls):
            cy = y_base + (row_idx * ys * direction)
            # High-Vis Gold Labels
            fnt = ("Verdana", int(10*self.zoom_scale), "bold")
            self.canvas.create_text(bx1+25*self.zoom_scale, cy, text=char, fill=self.COLORS["text_gold"], font=fnt)
            self.canvas.create_text(bx2-25*self.zoom_scale, cy, text=char, fill=self.COLORS["text_gold"], font=fnt)
            
            for i in range(30):
                self._draw_pro_hole(x_start + (i * xs), cy)

        # --- Tiered Numbering System ---
        num_y = y_base + (5.6 * ys * direction)
        for i in range(1, 31):
            cx = x_start + ((i - 1) * xs)
            
            if i % 5 == 0:
                # Primary Anchors (5, 10, 15, 20, 25, 30)
                # Larger, Bold, and High-Visibility Gold
                self.canvas.create_text(
                    cx, num_y, 
                    text=str(i), 
                    fill=self.COLORS["text_silver"], 
                    font=("Consolas", int(11 * self.zoom_scale), "bold")
                )
            else:
                # Secondary Markers (1, 2, 3, 4, 6...)
                # Smaller and "Ghosted" out to avoid visual noise
                self.canvas.create_text(
                    cx, num_y, 
                    text=str(i), 
                    fill="#5f5f6d", # Deep stealth grey
                    font=("Consolas", int(9 * self.zoom_scale))
                )

        # Neon Power Rails
        rail_y1 = y_base + (7.4 * ys * direction)
        rail_y2 = y_base + (8.8 * ys * direction)
        c1, c2 = (self.COLORS["rail_red"], self.COLORS["rail_blue"]) if direction == -1 else (self.COLORS["rail_blue"], self.COLORS["rail_red"])
        self._draw_rail_row(x_start, rail_y1, c1, bx1, bx2)
        self._draw_rail_row(x_start, rail_y2, c2, bx1, bx2)

    def _draw_rail_row(self, x_start, y, color, bx1, bx2):
        xs, s_gap = self.X_GAP * self.zoom_scale, self.SEGMENT_GAP * self.zoom_scale
        offset_x = ((29*xs) - ((24*xs) + (4*s_gap))) / 2
        sign = "+" if color == self.COLORS["rail_red"] else "−"
        
        # Glowing Signs
        self.canvas.create_text(bx1+25*self.zoom_scale, y, text=sign, fill=color, font=("Impact", int(16*self.zoom_scale)))
        self.canvas.create_text(bx2-25*self.zoom_scale, y, text=sign, fill=color, font=("Impact", int(16*self.zoom_scale)))

        for i in range(25):
            cx = x_start + offset_x + (i * xs) + ((i // 5) * s_gap)
            self._draw_pro_hole(cx, y, accent=color)


    # ==========================================================

    def get_node_at(self, x, y):
        """Returns (snapped_x, snapped_y, node_id) if near a hole, else None."""
        board_w, board_h = self._calculate_dimensions()
        x_mid, y_mid = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        xs, ys = self.X_GAP * self.zoom_scale, self.Y_GAP * self.zoom_scale
        
        # Calculate the starting point of the grid
        grid_x_start = x_mid - (board_w / 2) + (self.PADDING * self.zoom_scale)
        snap_radius = 12 * self.zoom_scale # Threshold to "catch" the probe

        # --- 1. Check Main Contact Grids (A-J) ---
        # Top Block (A-E) and Bottom Block (F-J)
        for direction, labels in [(-1, "ABCDE"), (1, "FGHIJ")]:
            y_base = y_mid + (1.6 * ys * direction)
            for row_idx, char in enumerate(labels[::-1] if direction == -1 else labels):
                cy = y_base + (row_idx * ys * direction)
                if abs(y - cy) < snap_radius:
                    # Check columns 1-30
                    col = int(round((x - grid_x_start) / xs))
                    if 0 <= col < 30:
                        cx = grid_x_start + (col * xs)
                        if abs(x - cx) < snap_radius:
                            return cx, cy, f"{char}{col + 1}"

        # --- 2. Check Power Rails ---
        s_gap = self.SEGMENT_GAP * self.zoom_scale
        offset_x = ((29 * xs) - ((24 * xs) + (4 * s_gap))) / 2
        rail_start_x = grid_x_start + offset_x

        for direction in [-1, 1]:
            y_base = y_mid + (1.6 * ys * direction)
            rails = [7.4, 8.8] # Y offsets for rails
            for r_idx, r_offset in enumerate(rails):
                ry = y_base + (r_offset * ys * direction)
                if abs(y - ry) < snap_radius:
                    # Determine Rail Name
                    rail_type = "RAIL_+" if (direction == -1 and r_idx == 0) or (direction == 1 and r_idx == 1) else "RAIL_-"
                    # Check rail holes (5 groups of 5)
                    for i in range(25):
                        rx = rail_start_x + (i * xs) + ((i // 5) * s_gap)
                        if abs(x - rx) < snap_radius:
                            return rx, ry, f"{rail_type}_{i+1}"
        return None
    

    def get_coords_of_node(self, node_id):
        """Finds pixel center of a Node ID (e.g. 'C15') at current zoom."""
        if not node_id: return None
        
        # Logic to extract Letter and Number
        try:
            row_char = node_id[0]
            col_num = int(node_id[1:]) - 1
            
            # Map Row to geometry
            # This must match your _draw_grid_block logic exactly
            row_data = {
                'A': (-1, 4), 'B': (-1, 3), 'C': (-1, 2), 'D': (-1, 1), 'E': (-1, 0),
                'F': (1, 0), 'G': (1, 1), 'H': (1, 2), 'I': (1, 3), 'J': (1, 4)
            }
            
            direction, row_idx = row_data[row_char]
            
            # Re-calculate geometry
            w, h, xs, ys = self._calculate_dimensions()
            x_mid, y_mid = self.canvas.winfo_width()/2, self.canvas.winfo_height()/2
            grid_x_start = x_mid - (w/2) + (self.PADDING * self.zoom_scale)
            
            y_base = y_mid + (1.6 * ys * direction)
            cy = y_base + (row_idx * ys * direction)
            cx = grid_x_start + (col_num * xs)
            
            return cx, cy
        except:
            return None