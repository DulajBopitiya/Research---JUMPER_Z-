import os
import subprocess
import sys
from pathlib import Path

def setup_project():
    print("🚀 Initializing JUMPER-Z Professional Environment...")
    
    # 1. Define Root Path (The script is in /scripts, so we go up 1 level)
    root = Path(__file__).resolve().parent.parent
    
    # 2. Verify Essential Static Folders (The ones that should be in Git)
    essential_dirs = ["assets", "config", "tools", "src"]
    for d in essential_dirs:
        if (root / d).exists():
            print(f"✅ Essential folder detected: {d}")
        else:
            (root / d).mkdir(parents=True, exist_ok=True)
            print(f"📁 Created missing essential folder: {d}")

    # 3. Handle Virtual Environment (.venv)
    venv_path = root / ".venv"
    if not venv_path.exists():
        print("📦 Creating Virtual Environment... (This may take a minute)")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        print("✅ Virtual Environment created.")
    else:
        print("✅ Virtual Environment already exists.")

    # 4. Check for Arduino-CLI Engine
    # This is critical for your App's logic
    cli_exe = root / "tools" / "arduino-cli.exe"
    if not cli_exe.exists():
        print("❌ ERROR: 'arduino-cli.exe' not found in /tools.")
        print("🔗 Please download it and place it in the /tools folder.")
        print("🔗 Link: https://github.com/arduino/arduino-cli/releases")
    else:
        print("✅ Arduino-CLI Engine detected.")

    # 5. Instructions for the Developer
    print("\n" + "="*50)
    print("✨ Setup Complete! To start developing:")
    if os.name == 'nt': # Windows
        print(f"1. Activate venv:    .venv\Scripts\Activate.ps1")
    else: # Mac/Linux
        print(f"1. Activate venv:    source .venv/bin/activate")
    
    print("2. Install Deps:      pip install -r requirements.txt")
    print("3. Run Application:   python main.py")
    print("="*50)

if __name__ == "__main__":
    setup_project()
