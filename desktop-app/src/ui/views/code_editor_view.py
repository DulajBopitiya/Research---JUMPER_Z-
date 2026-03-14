# src/ui/views/code_editor_view.py

from logging import root

import customtkinter as ctk
import tkinter as tk
from pathlib import Path

# --- CONSTANTS (Colours, Fonts) ---
COLOR_BG = "#1a1b26"
COLOR_PANEL = "#16161e"
COLOR_PANEL_ALT = "#24283b"
COLOR_BORDER = "#292e42"
COLOR_TEXT = "#a9b1d6"
CONSOLE_TEXT = "#00FF00"
COLOR_DIM = "#909bc9"
COLOR_ACTIVE = "#7aa2f7"
COLOR_DIM_NUM = "#5C6588"
COLOR_ACTIVE_NUM = "#d2bff5"
COLOR_STATUS = "#0b5d94"
COLOR_PROCESS = "#9ece6a"
COLOR_LINE_BG = "#222238"
COLOR_WHITE = "#f1f1f1"

FONT_EDITOR = ("Consolas", 14)
FONT_UI = ("Segoe UI", 12)
FONT_UI_BOLD = ("Segoe UI", 12, "bold")

PAIRS = {
        "(": ")",
        "{": "}",
        "[": "]",
        "\"": "\"",
        "'": "'"
    }

BRACE_PAIRS = {
    "(": ")",
    "{": "}",
    "[": "]",
}

REVERSE_BRACE_PAIRS = {v: k for k, v in BRACE_PAIRS.items()}

from src.ui.base_view import BaseFrame
from src.core.event_bus import event_bus
from src.core.events import Terminal, Build
from src.logic.project_context import project_context
from src.core.logging_config import get_logger
from src.core.log_events import L

from src.logic.highlight_engine import HighlightEngine

logger = get_logger(__name__)

class CodeEditorFrame(BaseFrame):
    FRAME_NAME = "Code Editor"

    def __init__(self, master, arduino_service=None, project_folder=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.project_folder: Path = project_context.get_active_project_path() or Path(".")
        self.sketch_file = self.project_folder / f"{self.project_folder.name}.ino"

        # Professional State Tracking
        self.open_files = {} # {Path: {"content": str, "cursor": str}}
        self.active_file = None

        self.highlighter = HighlightEngine()
        
        # 1. Setup the Grid
        self.grid_columnconfigure(0, minsize=250, weight=0) 
        self.grid_columnconfigure(1, weight=1)
        
        self.grid_rowconfigure(0, weight=0) # Top
        self.grid_rowconfigure(1, weight=1) # Editor (This takes the leftover space)
        self.grid_rowconfigure(2, weight=0) # Progress
        self.grid_rowconfigure(3, weight=0, minsize=180) # Console (Locked size)
        self.grid_rowconfigure(4, weight=0) # Status

        self.active_bottom_tab = "OUTPUT"

        # Build Components
        self._setup_top_bar()
        self._setup_sidebar()
        self._setup_editor_area()
        self._setup_progress_strip()
        self._setup_bottom_panel()
        self._setup_status_bar()

        # wire events
        self._register_events()

        # Startup: Open the main sketch file automatically
        if self.sketch_file.exists():
            self.open_file(self.sketch_file)

    def _register_events(self):
        event_bus.subscribe(Terminal.OUTPUT_RECEIVED, self._on_terminal_output)
        event_bus.subscribe(Build.BUILD_STARTED, self._on_build_started)
        event_bus.subscribe(Build.BUILD_PROGRESS, self._on_build_progress)
        event_bus.subscribe(Build.BUILD_SUCCEEDED, self._on_build_succeeded)
        event_bus.subscribe(Build.BUILD_FAILED, self._on_build_failed)
        


    def _setup_top_bar(self):
        self.top_bar = ctk.CTkFrame(self, height=50, fg_color=COLOR_PANEL, corner_radius=0)
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Build Button
        self.btn_build = ctk.CTkButton(self.top_bar, text="✓ Build", width=90, height=32, font=FONT_UI_BOLD, 
                                       fg_color=COLOR_PANEL_ALT, hover_color="#3E9715",
                                       command=self._compile)                                 
        self.btn_build.pack(side="left", padx=(20, 5), pady=10)

        # Upload Button
        self.btn_upload = ctk.CTkButton(self.top_bar, text="➜ Upload", width=90, height=32, font=FONT_UI_BOLD,
                                        fg_color=COLOR_ACTIVE, text_color=COLOR_PANEL, hover_color="#bb9af7",
                                        command=self._upload) 
        self.btn_upload.pack(side="left", padx=5)
        
        # ComboBoxes
        ctk.CTkComboBox(self.top_bar, values=["ESP32 Dev"], width=160, height=26,
                        fg_color=COLOR_PANEL_ALT, border_color=COLOR_BORDER).pack(side="left", padx=(60,5))
        
        ctk.CTkComboBox(self.top_bar, values=["COM3"], width=90, height=26,
                        fg_color=COLOR_PANEL_ALT, border_color=COLOR_BORDER).pack(side="left", padx=5)
        
        ctk.CTkLabel(self.top_bar, text="Baud:", font=FONT_UI, text_color=COLOR_DIM).pack(side="left", padx=(15,0))
        ctk.CTkComboBox(self.top_bar, values=["9600", "115200"], width=110, height=26,
                        fg_color=COLOR_PANEL_ALT, border_color=COLOR_BORDER).pack(side="left", padx=5)
        

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=0)
        self.sidebar.grid(row=1, column=0, rowspan=3, sticky="nsew")
        
        # Configure internal sidebar grid: 3 rows for the 3 sections
        self.sidebar.grid_rowconfigure(0, weight=3) # Explorer gets more space
        self.sidebar.grid_rowconfigure(1, weight=2) # Board Manager
        self.sidebar.grid_rowconfigure(2, weight=1) # Library Manager
        self.sidebar.grid_columnconfigure(0, weight=1)

        # 1. --- EXPLORER SECTION ---
        self.explorer_section = self._create_sidebar_box(self.sidebar, "EXPLORER", row=0)
        # Placeholder for files
        ctk.CTkLabel(self.explorer_section, text="main.ino\nconfig.h", 
                     font=FONT_UI, text_color=COLOR_TEXT, justify="left").pack(padx=20, pady=10, anchor="nw")

        # 2. --- BOARD MANAGER SECTION ---
        self.board_section = self._create_sidebar_box(self.sidebar, "BOARD MANAGER", row=1)
        ctk.CTkLabel(self.board_section, text="ESP32 Dev Module\n(Connected)", 
                     font=("Segoe UI", 11), text_color=COLOR_PROCESS).pack(padx=20, pady=10, anchor="nw")

        # 3. --- LIBRARY MANAGER SECTION ---
        self.library_section = self._create_sidebar_box(self.sidebar, "LIBRARY MANAGER", row=2)
        ctk.CTkEntry(self.library_section, placeholder_text="Search libs...", 
                     height=24, font=("Segoe UI", 11), fg_color=COLOR_BG, border_color=COLOR_BORDER).pack(fill="x", padx=10, pady=10)
    
    # =========================
    def _setup_editor_area(self):
        self.editor_container = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.editor_container.grid(row=1, column=1, sticky="nsew")
        self.editor_container.grid_rowconfigure(1, weight=1)
        self.editor_container.grid_columnconfigure(0, weight=1)

        # Tab bar
        self.tab_container = ctk.CTkFrame(self.editor_container, height=35, fg_color=COLOR_PANEL, corner_radius=0)
        self.tab_container.grid(row=0, column=0, sticky="ew")
        self.tab_container.grid_propagate(False)

        # Editor Body (Switching to Grid for stability)
        body = ctk.CTkFrame(self.editor_container, fg_color=COLOR_BG, corner_radius=0)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1) # Main text area expands
        body.grid_rowconfigure(0, weight=1)

        # Scrollbars
        self.v_scroll = ctk.CTkScrollbar(body, orientation="vertical", command=self._sync_v)
        self.h_scroll = ctk.CTkScrollbar(body, orientation="horizontal", command=self._sync_h)

        # Widgets
        self.line_num = tk.Text(body, width=5, padx=5, pady=15, font=FONT_EDITOR, 
                                bg=COLOR_LINE_BG, fg=COLOR_DIM, border=0, highlightthickness=0)
        
        self.txt = tk.Text(body, font=FONT_EDITOR, bg=COLOR_BG, fg=COLOR_WHITE, 
                           insertbackground=COLOR_ACTIVE, border=0, wrap="none", undo=True, 
                           pady=15, padx=15, highlightthickness=0, 
                           yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        
        #add tag style
        self.txt.tag_config("brace_match", background="#3b4261", foreground=COLOR_WHITE)
        
        self._setup_highlight_tags()
        self.txt.bind("<<Modified>>", self._on_text_changed)

        # Grid Placement
        self.line_num.grid(row=0, column=0, sticky="ns")
        self.txt.grid(row=0, column=1, sticky="nsew")
        self.v_scroll.grid(row=0, column=2, sticky="ns")
        self.h_scroll.grid(row=1, column=1, sticky="ew")

        # Initial State: Hidden
        self.v_scroll.grid_remove()
        self.h_scroll.grid_remove()

        # --- Editor Bindings ---
        # Combined change handler (Updates content + line numbers)
        self.txt.bind("<KeyRelease>", self._combined_key_release)
        
        # Click and Selection (Highlights the line number when you click)
        self.txt.bind("<Button-1>", lambda e: self.after(1, self._update_lines))
        
        # Scroll & Sync
        self.txt.bind("<MouseWheel>", lambda e: self.line_num.yview_scroll(int(-1*(e.delta/120)), "units"))
        self.txt.bind("<Configure>", lambda e: self._update_lines()) 
        self.txt.bind("<Control-MouseWheel>", self._handle_zoom)

        # Scrollbar Visibility
        self.txt.bind("<FocusIn>", self._show_scrollbars)
        self.txt.bind("<FocusOut>", self._hide_scrollbars)

        # Auto Indent + Smart Brace Logic
        self.txt.bind("<Return>", self._handle_enter)
        self.txt.bind("<Tab>", self._handle_tab)
        self.txt.bind("<Shift-Tab>", self._handle_shift_tab)
        self.txt.bind("<KeyPress>", self._handle_auto_close)
        self.txt.bind("<BackSpace>", self._handle_backspace)

        self.txt.bind("<ButtonRelease-1>", self._handle_cursor_move)
        
    def open_file(self, file_path: Path):
        """Loads a file into the tab system and switches view."""
        if file_path not in self.open_files:
            try:
                # Read content safely
                content = file_path.read_text(encoding='utf-8')
                self.open_files[file_path] = {
                    "content": content,
                    "cursor": "1.0"
                }
            except Exception as e:
                logger.error(f"Failed to open {file_path}: {e}")
                return

        self._switch_to_tab(file_path)

    def _combined_key_release(self, event=None):
        self._on_editor_change(event)
        self._handle_cursor_move(event)
        if hasattr(self, "_highlight_job"):
            self.after_cancel(self._highlight_job)

        self._highlight_job = self.after(120, self._run_highlight)

    def _on_editor_change(self, event=None):
        """Handle content changes and line updates"""
        if self.active_file:
            self.open_files[self.active_file]["content"] = self.txt.get("1.0", "end-1c")
        self._update_lines()

    def _switch_to_tab(self, file_path: Path):
        """Saves current state and swaps the text area content."""
        # 1. Save current work before switching
        if self.active_file and self.active_file in self.open_files:
            self.open_files[self.active_file]["content"] = self.txt.get("1.0", "end-1c")
            self.open_files[self.active_file]["cursor"] = self.txt.index("insert")

        # 2. Update active file and UI
        self.active_file = file_path
        data = self.open_files[file_path]

        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", data["content"])
        self.txt.mark_set("insert", data["cursor"])
        self.txt.see("insert")
        
        self._render_editor_tabs() # Redraw the top tab buttons
        self._update_lines()      # Refresh line numbers

    def _render_editor_tabs(self):
        """Draws the VS Code style tab row with close buttons."""
        for widget in self.tab_container.winfo_children():
            widget.destroy()

        for path in self.open_files:
            is_active = (path == self.active_file)
            
            # Tab Button Container
            tab_btn = ctk.CTkFrame(self.tab_container, height=35, corner_radius=0,
                                  fg_color=COLOR_BG if is_active else COLOR_PANEL)
            tab_btn.pack(side="left", padx=(0, 1))

            # File Name
            lbl = ctk.CTkLabel(tab_btn, text=path.name, padx=10, 
                              font=("Segoe UI", 11, "bold" if is_active else "normal"),
                              text_color=COLOR_WHITE if is_active else COLOR_DIM)
            lbl.pack(side="left")
            lbl.bind("<Button-1>", lambda e, p=path: self._switch_to_tab(p))

            # Close Button "×"
            close_btn = ctk.CTkLabel(tab_btn, text="×", width=20, font=("Arial", 14), 
                                    text_color=COLOR_DIM)
            close_btn.pack(side="right", padx=(0, 5))
            close_btn.bind("<Enter>", lambda e, c=close_btn: c.configure(text_color=COLOR_WHITE))
            close_btn.bind("<Leave>", lambda e, c=close_btn: c.configure(text_color=COLOR_DIM))
            close_btn.bind("<Button-1>", lambda e, p=path: self._close_tab(p))

            if is_active:
                tk.Frame(tab_btn, height=2, bg=COLOR_ACTIVE).place(relx=0, rely=0, relwidth=1)

    def _close_tab(self, path: Path):
        """Closes a tab without deleting the file."""
        if path in self.open_files:
            # Save content before closing
            if path == self.active_file:
                self.open_files[path]["content"] = self.txt.get("1.0", "end-1c")
            
            del self.open_files[path]
            
            # Switch to another tab if any remain
            if self.open_files:
                new_path = list(self.open_files.keys())[-1]
                self._switch_to_tab(new_path)
            else:
                self.active_file = None
                self.txt.delete("1.0", "end")
                self._render_editor_tabs()
                self._update_lines()
                
    def _update_lines(self, event=None):
        line_count = int(self.txt.index('end-1c').split('.')[0])
        current_line = int(self.txt.index('insert').split('.')[0])
        
        self.line_num.config(state="normal")
        self.line_num.delete("1.0", "end")
        
        # Batch insert all numbers
        lines_text = "\n".join(str(i) for i in range(1, line_count + 1)) + "\n"
        self.line_num.insert("1.0", lines_text)
        
        # 1. Apply 'dim' to EVERYTHING first
        self.line_num.tag_add("dim", "1.0", "end")
        self.line_num.tag_configure("dim", foreground=COLOR_DIM_NUM, justify='center')
        
        # 2. Apply 'active' to ONLY the current line
        self.line_num.tag_add("active", f"{current_line}.0", f"{current_line}.end+1c")
        self.line_num.tag_configure("active", foreground=COLOR_ACTIVE_NUM, justify='center')
        
        # 3. CRITICAL: Move the 'active' tag to the top of the priority stack
        self.line_num.tag_raise("active")
        
        # Sync scrolling
        self.line_num.yview_moveto(self.txt.yview()[0])
        self.line_num.config(state="disabled")

    def _handle_zoom(self, event):
        """Dynamically scales font size for both editor and line numbers."""
        # 1. Get current font configuration
        current_font = list(FONT_EDITOR) # Convert tuple to list: ["Consolas", 13]
        current_size = current_font[1]

        # 2. Determine zoom direction (event.delta is +/- 120)
        if event.delta > 0:
            new_size = current_size + 1
        else:
            new_size = current_size - 1

        # 3. Set zoom limits (Don't let it get too small or huge)
        if 8 <= new_size <= 48:
            current_font[1] = new_size
            new_font_tuple = tuple(current_font)
        
            # 4. Update both widgets
            self.txt.configure(font=new_font_tuple)
            self.line_num.configure(font=new_font_tuple)
        
            # 5. Refresh line numbers to match new height
            self._update_lines()
        
        return "break" # Prevents default scrolling while zooming

    def _sync_h(self, *args):
        self.txt.xview(*args)
        self.line_num.xview(*args)

    def _sync_v(self, *args):
        self.txt.yview(*args)
        self.line_num.yview(*args)

    def _show_scrollbars(self, event=None):
        # grid() remembers the row/column/sticky from the initial setup
        self.v_scroll.grid()
        self.h_scroll.grid()

    def _hide_scrollbars(self, event=None):
        # grid_remove hides the widget but keeps its grid settings in memory
        self.v_scroll.grid_remove()
        self.h_scroll.grid_remove()


    # ========================
    # Auto Indent
    def _handle_enter(self, event):
        line = self.txt.get("insert linestart", "insert")
        indent = len(line) - len(line.lstrip())

        stripped = line.strip()

        # Increase indent after {
        if stripped.endswith("{"):
            indent += 4

        # Decrease indent if current line starts with }
        if stripped.startswith("}"):
            indent = max(0, indent - 4)

        self.txt.insert("insert", "\n" + " " * indent)
        return "break"
    
    # Tab = 4 spaces
    def _handle_tab(self, event):
        self.txt.insert("insert", " " * 4)
        return "break"

    # Shift+Tab (Unindent)
    def _handle_shift_tab(self, event):
        line_start = self.txt.index("insert linestart")
        line_end = self.txt.index("insert lineend")
        line = self.txt.get(line_start, line_end)

        if line.startswith("    "):
            self.txt.delete(line_start, f"{line_start}+4c")

        return "break"

    # Auto-Close Brackets
    def _handle_auto_close(self, event):
        char = event.char
        if char in PAIRS:
            self.txt.insert("insert", PAIRS[char])
            self.txt.mark_set("insert", "insert-1c")

    # Smart Backspace (Delete Pair)
    def _handle_backspace(self, event):
        prev_char = self.txt.get("insert-1c", "insert")
        next_char = self.txt.get("insert", "insert+1c")

        if prev_char in PAIRS and PAIRS[prev_char] == next_char:
            self.txt.delete("insert-1c", "insert+1c")
            return "break"
        
    def _handle_cursor_move(self, event=None):
        self.txt.tag_remove("brace_match", "1.0", "end")

        index = self.txt.index("insert")
        prev_char = self.txt.get(f"{index}-1c", index)
        next_char = self.txt.get(index, f"{index}+1c")

        if prev_char in BRACE_PAIRS:
            self._highlight_matching_brace(index, prev_char, forward=True)

        elif prev_char in REVERSE_BRACE_PAIRS:
            self._highlight_matching_brace(index, prev_char, forward=False)

        elif next_char in BRACE_PAIRS:
            self._highlight_matching_brace(f"{index}+1c", next_char, forward=True)

        elif next_char in REVERSE_BRACE_PAIRS:
            self._highlight_matching_brace(index, next_char, forward=False)

    def _highlight_matching_brace(self, index, brace, forward=True):
        stack = 1
        # Define mapping to find the 'closing' brace relative to the current one
        # If forward, we look for the close of the brace. If backward, we look for the open.
        target_pair = BRACE_PAIRS.get(brace) if forward else REVERSE_BRACE_PAIRS.get(brace)
    
        # Configure search params
        search_kwargs = {
            "regexp": True,
            "backwards": not forward,
            "stopindex": "end" if forward else "1.0"
        }

        # Initial highlight for the bracket under cursor
        self.txt.tag_add("brace_match", f"{index}-1c", index) if forward else self.txt.tag_add("brace_match", index, f"{index}+1c")

        # Unified Search Loop
        search_index = index
        while True:
            search_index = self.txt.search(r"[()\[\]{}]", search_index, **search_kwargs)
            if not search_index: break

            char = self.txt.get(search_index)
        
            # Logic: Increment stack on same brace, decrement on matching pair
            if char == brace:
                stack += 1
            elif char == target_pair:
                stack -= 1

            if stack == 0:
                self.txt.tag_add("brace_match", search_index, f"{search_index}+1c")
                break
            
            search_index = f"{search_index}+1c" if forward else f"{search_index}-1c"

    def _run_highlight(self):
        code = self.txt.get("1.0", "end-1c")
        if not code.strip():
            return
        self.highlighter.highlight(self.txt, code)
        

    def _apply_highlight(self, root_node):
        text_line_count = int(self.txt.index("end-1c").split(".")[0])

        stack = [root_node]

        while stack:
            node = stack.pop()

            try:
                start_row, start_col = node.start_point
                end_row, end_col = node.end_point

                # Skip invalid / zero-length nodes
                if start_row > end_row:
                    continue
                if start_row == end_row and start_col == end_col:
                    continue

                # Prevent out-of-bounds rows
                if start_row + 1 > text_line_count:
                    continue

                start_index = f"{start_row + 1}.{start_col}"
                end_index = f"{end_row + 1}.{end_col}"

                node_type = node.type

                if node_type in ("string_literal",):
                    self.txt.tag_add("string", start_index, end_index)

                elif node_type in ("comment",):
                    self.txt.tag_add("comment", start_index, end_index)

                elif node_type in ("number_literal",):
                    self.txt.tag_add("number", start_index, end_index)

                elif node_type in ("preproc_include", "preproc_def", "preproc_if"):
                    self.txt.tag_add("preproc", start_index, end_index)

                elif node_type in ("primitive_type", "type_identifier"):
                    self.txt.tag_add("type", start_index, end_index)

                elif node_type in ("identifier",):
                    parent = node.parent
                    if parent and parent.type == "function_declarator":
                        self.txt.tag_add("func", start_index, end_index)

                elif node_type.endswith("_statement"):
                    self.txt.tag_add("kw", start_index, end_index)

            except Exception:
                logger.warning(f"Failed to highlight node of type '{node_type}' at {start_index}")

            # Push children AFTER processing
            for child in reversed(node.children):
                stack.append(child)

    def _setup_highlight_tags(self):

        # Configure colors (Tokyonight)
        self.txt.tag_configure("kw", foreground="#7aa2f7")
        self.txt.tag_configure("type", foreground="#2ac3de")
        self.txt.tag_configure("string", foreground="#9ece6a")
        self.txt.tag_configure("comment", foreground="#565f89")
        self.txt.tag_configure("number", foreground="#ff9e64")
        self.txt.tag_configure("func", foreground="#bb9af7")
        self.txt.tag_configure("preproc", foreground="#c0caf5")
        self.txt.tag_configure("constant", foreground="#f7768e") # Red-ish for macros
        self.txt.tag_configure("register", foreground="#e0af68")
        
        # Ensure hierarchy (Force important tags on top)
        self.txt.tag_raise("func")
        self.txt.tag_raise("kw")
        self.txt.tag_raise("constant")

    def _on_text_changed(self, event=None):
        # Check if the text was actually modified
        if self.txt.edit_modified():
            content = self.txt.get("1.0", "end-1c")
            
            # Call your highlighter
            self.highlighter.highlight(self.txt, content)
            
            # Reset the modified flag so it triggers again on next keypress
            self.txt.edit_modified(False)








    # =========================
    def _setup_progress_strip(self):
        self.progress_frame = ctk.CTkFrame(self, height=4, fg_color=COLOR_BG, corner_radius=0)
        self.progress_frame.grid(row=2, column=1, sticky="ew")
        self.progress_frame.grid_propagate(False)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=2, corner_radius=0, 
                                               fg_color=COLOR_PANEL, progress_color=COLOR_PROCESS, border_width=0)
        self.progress_bar.pack(fill="x", pady=1)
        self.progress_bar.set(0)

    # =========================
    def _setup_bottom_panel(self):
        self.bottom_console = ctk.CTkFrame(self, fg_color=COLOR_PANEL, corner_radius=0)
        self.bottom_console.grid(row=3, column=1, sticky="nsew")
        self.bottom_console.pack_propagate(False) 

        self.console_header = ctk.CTkFrame(self.bottom_console, height=35, fg_color=COLOR_PANEL)
        self.console_header.pack(fill="x", side="top")

        self.console_tabs = {}
        self.tab_names = ["OUTPUT", "TERMINAL", "SERIAL MONITOR", "PROBLEMS"]
        
        for name in self.tab_names:
            tab_frame = ctk.CTkFrame(self.bottom_console, fg_color=COLOR_PANEL, corner_radius=0)
            tab_frame.grid_rowconfigure(0, weight=1)
            tab_frame.grid_columnconfigure(0, weight=1)
            
            v_scroll = ctk.CTkScrollbar(tab_frame, orientation="vertical")
            v_scroll.grid(row=0, column=1, sticky="ns")
            v_scroll.grid_remove()
            
            txt = tk.Text(tab_frame, bg=COLOR_PANEL, fg=CONSOLE_TEXT, 
                          font=("Consolas", 12), border=0, padx=20, pady=5,
                          insertbackground=COLOR_ACTIVE, undo=True, wrap="word",
                          state="disabled", yscrollcommand=v_scroll.set)
            txt.grid(row=0, column=0, sticky="nsew")
            v_scroll.configure(command=txt.yview)
  
            # --- THE HOVER LOGIC ---
            # Show when mouse enters the tab area or clicks
            tab_frame.bind("<Enter>", lambda e, s=v_scroll: s.grid())
            txt.bind("<FocusIn>", lambda e, s=v_scroll: s.grid())

            # Hide when mouse leaves (unless it has focus)
            tab_frame.bind("<Leave>", lambda e, s=v_scroll, t=txt: 
                           s.grid_remove() if self.focus_get() != t else None)
            txt.bind("<FocusOut>", lambda e, s=v_scroll: s.grid_remove())
        
            if name == "TERMINAL":
                self.terminal_input = ctk.CTkEntry(
                    tab_frame, placeholder_text="Enter system command...",
                    font=("Consolas", 12), fg_color=COLOR_BG, border_color=COLOR_BORDER, height=28)
                self.terminal_input.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
                self.terminal_input.bind("<Return>", self._send_terminal_command)


            self.console_tabs[name] = {"frame": tab_frame, "text": txt}
            
        # Initial render
        self._render_bottom_tabs()
        self._switch_tab("OUTPUT")

    # =========================
    def _setup_status_bar(self):     # ====> DUMMY FUNCTION
        status = ctk.CTkFrame(self, height=22, fg_color=COLOR_STATUS, corner_radius=0)
        status.grid(row=4, column=0, columnspan=2, sticky="ew")
        ctk.CTkLabel(status, text="DEVELOPER MODE | UTF-8 | Arduino ESP32", font=("Segoe UI", 10, "bold"), 
                     text_color=COLOR_WHITE).pack(side="right", padx=20)

    # ------------------------
    def _compile(self):      # DUMMY FUNCTION ----> WENS KRPN MEEKA
        self._save_sketch()
        self._clear_output_tab(switch=True)
        self._switch_tab("OUTPUT")
        event_bus.emit(Build.COMPILE_REQ)
        """def run():
            for i in range(1, 101):
                time.sleep(0.015)
                self.progress_bar.set(i / 100)
            time.sleep(0.5)
            self.progress_bar.set(0)
        threading.Thread(target=run).start()"""

    def _upload(self):
        self._save_sketch()
        self._clear_output_tab(switch=True)
        self._switch_tab("OUTPUT")
        event_bus.emit(Build.UPLOAD_REQ)

    def _save_sketch(self):
        self.sketch_file.parent.mkdir(parents=True, exist_ok=True)
        content = self.txt.get("0.0", "end-1c")
        self.sketch_file.write_text(content)

    def _clear_output_tab(self, switch=True):
        output = self.console_tabs.get("OUTPUT")
        if not output:
            return

        text_widget = output["text"]
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.configure(state="disabled")

        if switch:
            self._switch_tab("OUTPUT")
    
    # ------------------------
    def _create_sidebar_box(self, master, title, row):
        """Helper to create a sleek section box with a header"""
        # Container
        container = ctk.CTkFrame(master, fg_color="transparent", corner_radius=0)
        container.grid(row=row, column=0, sticky="nsew")
        
        # Header bar
        header = ctk.CTkFrame(container, height=28, fg_color=COLOR_PANEL_ALT, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Sleek top border/line for the header
        line = tk.Frame(header, height=1, bg=COLOR_BORDER)
        line.pack(side="top", fill="x")
        
        # Title Label
        ctk.CTkLabel(header, text=f" ▾ {title}", font=("Segoe UI", 10, "bold"), 
                     text_color=COLOR_WHITE).pack(side="left", padx=10)
        
        # Content Area (where widgets for this section go)
        content = ctk.CTkFrame(container, fg_color="transparent", corner_radius=0)
        content.pack(fill="both", expand=True)
        
        return content

    # ------------------------
    def _render_bottom_tabs(self):
        # Clear existing buttons to prevent stacking
        for widget in self.console_header.winfo_children():
            widget.destroy()

        for name in self.tab_names:
            active = (name == self.active_bottom_tab)
            
            # Create tab button
            btn = ctk.CTkButton(
                self.console_header, text=name, width=120, height=32, corner_radius=4,
                font=("Segoe UI", 10, "bold" if active else "normal"), 
                fg_color="#1C1C2B" if active else "transparent", 
                text_color=COLOR_WHITE if active else COLOR_DIM, hover_color=COLOR_PANEL_ALT,
                command=lambda n=name: self._switch_tab(n)
            )
            btn.pack(side="left", padx=5, pady=(2, 0))
            
            if active:
                # Sleek underline for the active tab
                underline = tk.Frame(btn, height=2, bg=COLOR_ACTIVE)
                underline.place(relx=0.125, rely=0.9, relwidth=0.75)
    
    def _switch_tab(self, name):
        """Switches the visible tab frame"""
        # Hide previous frame
        if hasattr(self, 'active_bottom_tab') and self.active_bottom_tab in self.console_tabs:
            self.console_tabs[self.active_bottom_tab]["frame"].pack_forget()

        self.active_bottom_tab = name
        # Show new frame
        self.console_tabs[name]["frame"].pack(fill="both", expand=True)
        self._render_bottom_tabs()

    def write_to_tab(self, tab_name, message):
        """Thread-safe way to write to any disabled tab"""
        if tab_name in self.console_tabs:
            widget = self.console_tabs[tab_name]["text"]
            widget.configure(state="normal") # Unlock
            widget.insert("end", f"{message}\n")
            widget.see("end")
            widget.configure(state="disabled") # Re-lock

    # NEW ==================================================

    def _send_terminal_command(self, event=None):
        command = self.terminal_input.get().strip()
        if not command:
            return "break"

        event_bus.emit(Terminal.COMMAND_REQ, command=command)
        self.terminal_input.delete(0, "end")
        return "break"

    def _on_terminal_output(self, **kwargs):
        line = kwargs.get("line", "")
        if line:
            self.after(0, lambda: self.write_to_tab("TERMINAL", line))


    # Build Event Handlers
    def _on_build_started(self, **kwargs):
        def ui():
            # Reset progress
            self.progress_bar.set(0)

            # Clear output and focus it
            self._clear_output_tab(switch=True)
            self.write_to_tab("OUTPUT", "⏳ Compiling sketch...\n")

            # Disable controls (if refs exist)
            if hasattr(self, "btn_build"):
                self.btn_build.configure(state="disabled")
            if hasattr(self, "btn_upload"):
                self.btn_upload.configure(state="disabled")

        self.after(0, ui)


    def _on_build_progress(self, **kwargs):
        progress = kwargs.get("progress")
        if progress is None:
            return

        def ui():
            # Convert 0–100 → 0.0–1.0
            value = max(0.0, min(progress / 100.0, 1.0))
            self.progress_bar.set(value)

        self.after(0, ui)

    def _on_build_succeeded(self, **kwargs):
        def ui():
            self.progress_bar.set(1.0)
            self.write_to_tab("OUTPUT", "✅ Build succeeded!\n")

            # Re-enable controls
            if hasattr(self, "btn_build"):
                self.btn_build.configure(state="normal")
            if hasattr(self, "btn_upload"):
                self.btn_upload.configure(state="normal")

        self.after(0, ui)

    def _on_build_failed(self, **kwargs):
        error_msg = kwargs.get("error", "Unknown build error")

        def ui():
            # Reset progress
            self.progress_bar.set(0)
            self.write_to_tab("OUTPUT", f"❌ Build failed:\n{error_msg}\n")

            # Re-enable controls
            if hasattr(self, "btn_build"):
                self.btn_build.configure(state="normal")
            if hasattr(self, "btn_upload"):
                self.btn_upload.configure(state="normal")

        self.after(0, ui)
    # ------------------------
    # Lifecycle
    # ------------------------
    def on_show(self):
        logger.info("CodeEditorFrame shown", extra={"event_id": L.VW.VIEW_SHOWN})

    def on_hide(self):
        logger.info("CodeEditorFrame hidden", extra={"event_id": L.VW.VIEW_HIDDEN})
