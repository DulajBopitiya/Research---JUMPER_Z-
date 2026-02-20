import customtkinter as ctk

# -------------------------------
# CONFIGURATION
# -------------------------------
ROWS = 31
TOP_COLUMNS = "ABCDE"
BOTTOM_COLUMNS = "FGHIJ"
RAIL_SEGMENTS = 5
HOLE_RADIUS = 6
X_START, Y_START = 120, 120
X_GAP, Y_GAP = 25, 25
DIVIDER_HEIGHT = 25
POWER_RAIL_GAP = 80   # vertical gap from top rows
SEGMENT_GAP = 30      # horizontal gap between 5-hole segments
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 450

# -------------------------------
# CONNECTION LOGIC
# -------------------------------
breadboard_connections = {}

# Main rows: top and bottom
for r in range(1, ROWS + 1):
    breadboard_connections[f"row_top_{r}"] = [f"{r}{c}" for c in TOP_COLUMNS]
    breadboard_connections[f"row_bottom_{r}"] = [f"{r}{c}" for c in BOTTOM_COLUMNS]

# Power rails (5 segments, each 5 holes connected)
for rail_name in ["VCC_TOP", "GND_TOP", "VCC_BOTTOM", "GND_BOTTOM"]:
    for seg in range(5):
        start = seg * RAIL_SEGMENTS + 1
        segment = [f"{rail_name}_{i}" for i in range(start, start + RAIL_SEGMENTS)]
        breadboard_connections[f"{rail_name}_seg{seg+1}"] = segment

# Reverse lookup: hole → node
hole_to_node = {hole: node for node, holes in breadboard_connections.items() for hole in holes}

# -------------------------------
# GUI SETUP
# -------------------------------
ctk.set_appearance_mode("dark")
root = ctk.CTk()
root.title("Breadboard Layout")
root.geometry(f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}")

canvas = ctk.CTkCanvas(root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT,
                        bg="#2b2b2b", highlightthickness=0)
canvas.pack(fill="both", expand=True, padx=10, pady=10)

hole_items = {}

# -------------------------------
# TOP POWER RAILS
# -------------------------------
top_rail_y_vcc = Y_START - POWER_RAIL_GAP
top_rail_y_gnd = top_rail_y_vcc + Y_GAP

canvas.create_text(X_START - 30, top_rail_y_vcc, text="+", fill="red", font=("Helvetica", 12, "bold"))
canvas.create_text(X_START - 30, top_rail_y_gnd, text="–", fill="blue", font=("Helvetica", 12, "bold"))

for seg in range(5):
    for i in range(RAIL_SEGMENTS):
        x = X_START + seg * (RAIL_SEGMENTS * X_GAP + SEGMENT_GAP) + i * X_GAP + 15
        # VCC
        hole_name = f"VCC_TOP_{seg * RAIL_SEGMENTS + i + 1}"
        circle = canvas.create_oval(x - HOLE_RADIUS, top_rail_y_vcc - HOLE_RADIUS,
                                    x + HOLE_RADIUS, top_rail_y_vcc + HOLE_RADIUS,
                                    fill="#550000", outline="red")
        hole_items[circle] = hole_name
        # GND
        hole_name = f"GND_TOP_{seg * RAIL_SEGMENTS + i + 1}"
        circle = canvas.create_oval(x - HOLE_RADIUS, top_rail_y_gnd - HOLE_RADIUS,
                                    x + HOLE_RADIUS, top_rail_y_gnd + HOLE_RADIUS,
                                    fill="#000055", outline="blue")
        hole_items[circle] = hole_name

# End labels
x_last = X_START + (5 * RAIL_SEGMENTS * X_GAP + 4 * SEGMENT_GAP) + 15  # last hole X coordinate
canvas.create_text(x_last + 20, top_rail_y_vcc, text="+", fill="red", font=("Helvetica", 12, "bold"))
canvas.create_text(x_last + 20, top_rail_y_gnd, text="–", fill="blue", font=("Helvetica", 12, "bold"))

# -------------------------------
# TOP GRID (A–E)
# -------------------------------
for i, col in enumerate(TOP_COLUMNS):
    y = Y_START + i * Y_GAP
    canvas.create_text(X_START - 30, y, text=col, fill="#ddd", font=("Helvetica", 10, "bold"))

    row_end_x = X_START + (ROWS - 1) * X_GAP + 30  # right end, some extra margin
    canvas.create_text(row_end_x, y, text=col, fill="#ddd", font=("Helvetica", 10, "bold"))

    for r in range(1, ROWS + 1):
        x = X_START + (r - 1) * X_GAP
        hole_name = f"{r}{col}"
        circle = canvas.create_oval(x - HOLE_RADIUS, y - HOLE_RADIUS,
                                    x + HOLE_RADIUS, y + HOLE_RADIUS,
                                    fill="#444", outline="#999")
        hole_items[circle] = hole_name

# -------------------------------
# CENTER DIVIDER
# -------------------------------
divider_top = Y_START + len(TOP_COLUMNS) * Y_GAP + 5
divider_bottom = divider_top + DIVIDER_HEIGHT
canvas.create_rectangle(X_START - 40, divider_top,
                        X_START + (ROWS - 1) * X_GAP + 40, divider_bottom,
                        outline="#888", width=2)
canvas.create_text(X_START + (ROWS - 1) * X_GAP / 2, (divider_top + divider_bottom)/2,
                   text="Center Divider", fill="#999",
                   font=("Helvetica", 11, "bold", "italic"))

# -------------------------------
# BOTTOM GRID (F–J)
# -------------------------------
bottom_y_start = divider_bottom + 30
for i, col in enumerate(BOTTOM_COLUMNS):
    y = bottom_y_start + i * Y_GAP
    canvas.create_text(X_START - 30, y, text=col, fill="#ddd", font=("Helvetica", 10, "bold"))  # left
    canvas.create_text(row_end_x, y, text=col, fill="#ddd", font=("Helvetica", 10, "bold"))     # right

    for r in range(1, ROWS + 1):
        x = X_START + (r - 1) * X_GAP
        hole_name = f"{r}{col}"
        circle = canvas.create_oval(x - HOLE_RADIUS, y - HOLE_RADIUS,
                                    x + HOLE_RADIUS, y + HOLE_RADIUS,
                                    fill="#444", outline="#999")
        hole_items[circle] = hole_name

# -------------------------------
# BOTTOM POWER RAILS
# -------------------------------
bottom_rail_y_vcc = bottom_y_start + len(BOTTOM_COLUMNS) * Y_GAP + 20
bottom_rail_y_gnd = bottom_rail_y_vcc + Y_GAP

canvas.create_text(X_START - 30, bottom_rail_y_vcc, text="+", fill="red", font=("Helvetica", 12, "bold"))
canvas.create_text(X_START - 30, bottom_rail_y_gnd, text="–", fill="blue", font=("Helvetica", 12, "bold"))

end_label_offset = 30  # space between last hole and the label
canvas.create_text(x + end_label_offset, bottom_rail_y_vcc, text="+", fill="red", font=("Helvetica", 12, "bold"))
canvas.create_text(x + end_label_offset, bottom_rail_y_gnd, text="–", fill="blue", font=("Helvetica", 12, "bold"))

for seg in range(5):
    for i in range(RAIL_SEGMENTS):
        x = X_START + seg * (RAIL_SEGMENTS * X_GAP + SEGMENT_GAP) + i * X_GAP + 15
        # VCC
        hole_name = f"VCC_BOTTOM_{seg * RAIL_SEGMENTS + i + 1}"
        circle = canvas.create_oval(x - HOLE_RADIUS, bottom_rail_y_vcc - HOLE_RADIUS,
                                    x + HOLE_RADIUS, bottom_rail_y_vcc + HOLE_RADIUS,
                                    fill="#550000", outline="red")
        hole_items[circle] = hole_name
        # GND
        hole_name = f"GND_BOTTOM_{seg * RAIL_SEGMENTS + i + 1}"
        circle = canvas.create_oval(x - HOLE_RADIUS, bottom_rail_y_gnd - HOLE_RADIUS,
                                    x + HOLE_RADIUS, bottom_rail_y_gnd + HOLE_RADIUS,
                                    fill="#000055", outline="blue")
        hole_items[circle] = hole_name

# -------------------------------
# COLUMN NUMBERS (top and bottom)
# -------------------------------
for r in range(1, ROWS + 1):
    x = X_START + (r - 1) * X_GAP
    canvas.create_text(x, Y_START - 25, text=str(r), fill="#ddd", font=("Helvetica", 9, "bold"))
    canvas.create_text(x, bottom_rail_y_gnd - 45, text=str(r), fill="#ddd", font=("Helvetica", 9, "bold"))

# -------------------------------
# NODE HIGHLIGHT / INTERACTION (Single Hole Only)
# -------------------------------
node_label = canvas.create_text(0, 0, text="", anchor="nw", fill="#00ff66", font=("Helvetica", 10, "bold"))
canvas.itemconfig(node_label, state="hidden")

def highlight_single_hole(cid):
    """Highlight only the clicked hole."""
    for c, hole in hole_items.items():
        if c == cid:
            canvas.itemconfig(c, fill="#00ff66")
        else:
            # Reset all other holes to default colors
            if "VCC" in hole:
                canvas.itemconfig(c, fill="#550000")
            elif "GND" in hole:
                canvas.itemconfig(c, fill="#000055")
            else:
                canvas.itemconfig(c, fill="#444")

def clear_highlight():
    """Reset all holes to default color."""
    for cid, hole in hole_items.items():
        if "VCC" in hole:
            canvas.itemconfig(cid, fill="#550000")
        elif "GND" in hole:
            canvas.itemconfig(cid, fill="#000055")
        else:
            canvas.itemconfig(cid, fill="#444")
    canvas.itemconfig(node_label, state="hidden")

def on_left_click(event):
    clicked = canvas.find_closest(event.x, event.y)
    if not clicked:
        return
    cid = clicked[0]
    if cid in hole_items:
        highlight_single_hole(cid)
        hole = hole_items[cid]
        coords = canvas.coords(cid)
        cx = (coords[0] + coords[2]) / 2
        cy = coords[1] - 18
        canvas.coords(node_label, cx + 12, cy)
        canvas.itemconfig(node_label, text=f"{hole}", state="normal")

def on_right_click(event):
    clear_highlight()

canvas.bind("<Button-1>", on_left_click)
canvas.bind("<Button-3>", on_right_click)

# -------------------------------
# RUN APP
# -------------------------------


if __name__ == "__main__":
    root.mainloop()