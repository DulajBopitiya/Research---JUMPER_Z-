# Development & Engineering Guidelines

## 🔧 Prerequisites
- **Python**: 3.12 (Strictly enforced via `.venv`)
- **CLI Engine**: `arduino-cli` v0.35.x (Stored in `/tools`)
- **GUI Framework**: [Insert your framework here, e.g., PySide6 or Tkinter]

## 🛠 Project Standards
1. **Branching**: All work must occur on `feat/` or `fix/` branches.
2. **Code Style**: PEP 8 compliance.
3. **Internal Folders**:
   - `runtime/`: Strictly for local logs and cache. NEVER commit these.
   - `tests/scratch/`: Safe zone for MF_*.py experimental scripts.

## ⚙️ Setting Up the Arduino CLI Engine
The `arduino-cli.exe` must be placed in `desktop-app/tools/`. 
The application expects the following configuration:
- Config file: `tools/arduino-cli.yaml`
- Data folder: `tools/data/`

## 🧪 Testing Protocol
Before pushing to `main`, run:
- Unit tests: `pytest tests/unit`
- Integration: `pytest tests/integration`
