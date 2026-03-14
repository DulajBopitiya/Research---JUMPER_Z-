# main.py

from src.bootstrap import bootstrap
from src.ui.app_shell import AppShell

def main():
    bootstrap()

    app = AppShell()
    app.mainloop()

if __name__ == "__main__":
    main()

    
"""
# main.py

import sys
import tkinter.messagebox as messagebox
from src.bootstrap import bootstrap
from src.ui.app_shell import AppShell

def main():
    try:
        bootstrap()
    except Exception as e:
        # In an .exe, this creates a real Windows alert box
        messagebox.showerror(
            "Initialization Error", 
            f"JUMPER-Z failed to start.\n\nError: {e}\n\nPlease check folder permissions."
        )
        sys.exit(1)

    app = AppShell()
    app.mainloop()

if __name__ == "__main__":
    main()

"""