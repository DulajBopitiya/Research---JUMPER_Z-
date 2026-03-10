# Development & Engineering Guidelines

## 🔧 Prerequisites
- **Python**: 3.12 (Strictly enforced via `.venv`)
- **CLI Engine**: `arduino-cli` v0.35.x (Stored in `/tools`)
- **GUI Framework**: customtkinter

## 🛠 Project Standards
1. **Branching**: All work must occur on `feat/` or `fix/` branches.
2. **Code Style**: PEP 8 compliance.
3. **Internal Folders**:
   - `runtime_dev/`: Local logs, user config, and Wokwi staging. (Automatically ignored by Git).
   - `config/`: Shipped static assets (e.g., `language_config.json`).
   - `projects/`: Default local workspace for `.ino` files.

## ⚙️ Setting Up the Arduino CLI Engine
The `arduino-cli.exe` must be placed in the root `/tools/` folder. 
The application manages paths automatically via `src/core/config.py`. 
- **Binary Path**: `tools/arduino-cli.exe`
- **Data Isolation**: The app is designed to run the CLI in "Local Mode" to avoid system-wide conflicts.

## 🧪 Testing Protocol
Before pushing to `main`, run:
- Unit tests: `pytest tests/unit`
