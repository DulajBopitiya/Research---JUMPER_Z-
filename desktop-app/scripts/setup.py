import os
import subprocess
import sys
from pathlib import Path

def setup_project():
    print("🚀 Initializing JP-Platform Professional Environment...")
    
    # 1. Define Root Path (relative to this script)
    root = Path(__file__).parent.parent
    
    # 2. Ensure Professional Directory Structure exists
    required_dirs = [
        "runtime/logs", "runtime/cache", "runtime/user",
        "projects", "tools", "assets", "config"
    ]
    for d in required_dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
        print(f"✅ Verified folder: {d}")

    # 3. Handle Virtual Environment (.venv)
    venv_path = root / ".venv"
    if not venv_path.exists():
        print("📦 Creating Virtual Environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
    else:
        print("✅ Virtual Environment already exists.")

    # 4. Check for Arduino-CLI Engine
    cli_exe = root / "tools" / "arduino-cli.exe"
    if not cli_exe.exists():
        print("⚠️  WARNING: 'arduino-cli.exe' not found in /tools.")
        print("🔗 Please download it from: https://github.com")
    else:
        print("✅ Arduino-CLI Engine detected.")

    print("\n✨ Setup Complete! To start developing:")
    print(f"1. Activate venv: {'.venv\\Scripts\\activate' if os.name == 'nt' else 'source .venv/bin/activate'}")
    print("2. Install dependencies: pip install -r requirements.txt")

if __name__ == "__main__":
    setup_project()
