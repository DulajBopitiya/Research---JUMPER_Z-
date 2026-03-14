# JUMPER-Z: Desktop IDE & Simulation Suite

A high-performance desktop interface for integrated Arduino development, 
Wokwi circuit simulation, and real-time hardware telemetry.

## 🚀 Key Features
- **Custom IDE Engine**: Powered by `arduino-cli` for seamless compilation.
- **Circuit Simulation**: Deep integration with Wokwi for virtual prototyping.
- **Staging Area**: Temporary workspace for Wokwi fetches before permanent saving.
- **Modular Core**: Decoupled event-driven architecture.

## 🏗 High-Level Architecture
The application follows a **Clean Architecture** pattern:
- `src/core`: State management, Event Bus, and Tasking logic.
- `src/ui`: Modular Shell/Component UI system based on CustomTkinter.
- `src/logic`: Wokwi pipelines and project context management.
- `src/services`: Hardware & CLI abstraction layers.

## 📦 Getting Started
1. Ensure Python 3.12+ is installed.
2. Run the setup script: `python scripts/setup.py`
3. Activate the environment: `.venv\Scripts\activate` (Windows)
4. Install requirements: `pip install -r requirements.txt`
5. Launch the app: `python main.py`
