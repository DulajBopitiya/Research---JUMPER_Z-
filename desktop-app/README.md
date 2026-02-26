# JP-Platform: Desktop IDE & Simulation Suite

A high-performance desktop interface for integrated Arduino development, 
Wokwi circuit simulation, and real-time hardware telemetry.

## 🚀 Key Features
- **Custom IDE Engine**: Powered by `arduino-cli` for seamless compilation.
- **Circuit Simulation**: Deep integration with Wokwi for virtual prototyping.
- **Hardware Telemetry**: Real-time serial monitoring and oscilloscope views.
- **Modular Core**: Decoupled event-driven architecture.

## 🏗 High-Level Architecture
The application follows a **Clean Architecture** pattern:
- `app/core`: State management, Event Bus, and Tasking logic.
- `app/ui`: Modular Shell/Component UI system.
- `app/services`: Hardware & CLI abstraction layers.

## 📦 Getting Started
1. Ensure Python 3.12+ is installed.
2. Run the bootstrap script: `python scripts/setup.py`
3. Launch the app: `python src/main.py`
