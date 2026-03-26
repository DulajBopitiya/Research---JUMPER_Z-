# src/controller/AppController.py


from pathlib import Path
from typing import Optional

from logging import getLogger
from src.core.event_bus import event_bus
from src.core.events import HW, Build, Serial, Terminal, Events
from src.core.log_events import L
from src.core.state import app_state
from src.core.state_keys import StateKeys
from src.core.context import HardwareContext, BuildContext, SerialContext, EditorContext

from src.services.terminal_service import TerminalService
from src.services.serial_service import SerialService
from src.logic.project_context import (
    arduino_service,
    project_context
)

logger = getLogger(__name__)

class AppController:
    """
    Central application policy & orchestration layer.

    Responsibilities:
    - Owns application-level decisions
    - Listens to intent events
    - Updates global state
    - Delegates execution to services
    """

    # ============================================================
    # Lifecycle
    # ============================================================

    def __init__(self):
        # --- Context ownership ---
        self.hardware_ctx = HardwareContext(
            boards=[],
            ports=[],
            selected_board=None,
            selected_port=None,
            selected_fqbn=None,
            connected=False,
            error=None,
        )

        self.serial_ctx = SerialContext(
            is_open=False,
            port=None,
            baudrate=None,
            busy=False,
            last_error=None,
        )

        self.build_ctx = BuildContext(
            compiling=False,
            uploading=False,
            progress=None,
            last_error=None,
        )

        self.editor_ctx = EditorContext()

        #===========================================================
        # ---- Project context ----
        self.project_folder: Path = project_context.get_active_project_path()
        project_context.save_active_project_path(self.project_folder)
        #===========================================================

        # ---- Services ----
        self.serial_service = SerialService()

        self.terminal = TerminalService()
        self.terminal.start()
        
        # Event wiring
        self._register_hardware_events()
        self._register_serial_events()
        self._register_build_events()
        self._register_terminal_events()
        self._register_ui_events()


    # ============================================================
    # EVENT REGISTRATION
    # ============================================================
    def _register_hardware_events(self):
        event_bus.subscribe(HW.REFRESH_REQ, self._on_hardware_refresh_requested)
        event_bus.subscribe(HW.SELECT_BOARD_REQ, self._on_board_selected)
        event_bus.subscribe(HW.SELECT_PORT_REQ, self._on_port_selected)

    def _register_serial_events(self):
        # Requests
        event_bus.subscribe(Serial.OPEN_REQUESTED, self._on_serial_open_requested)
        event_bus.subscribe(Serial.CLOSE_REQUESTED, self._on_serial_close_requested)
        event_bus.subscribe(Serial.WRITE_REQUESTED, self._on_serial_write_requested)

        # Facts
        event_bus.subscribe(Serial.OPENED, self._on_serial_opened)
        event_bus.subscribe(Serial.CLOSED, self._on_serial_closed)
        event_bus.subscribe(Serial.BUSY, self._on_serial_busy)
        event_bus.subscribe(Serial.DATA_RECEIVED, self._on_serial_data_received)
        event_bus.subscribe(Serial.SERIAL_WRITE_ACK, self._on_serial_write_ack)
        event_bus.subscribe(Serial.SERIAL_ERROR, self._on_serial_error)

    def _register_build_events(self):
        event_bus.subscribe(Build.COMPILE_REQ, self._on_build_compile_requested)
        event_bus.subscribe(Build.UPLOAD_REQ, self._on_build_upload_requested)
        event_bus.subscribe(Build.ABORT_REQ, self._on_build_abort_requested)

    def _register_terminal_events(self):
        event_bus.subscribe(Terminal.COMMAND_REQ, self._on_terminal_command_requested)
        event_bus.subscribe(Terminal.OUTPUT_RECEIVED, self._on_terminal_output_received)
        event_bus.subscribe(Terminal.COMMAND_FINISHED, self._on_terminal_command_finished)
        event_bus.subscribe(Terminal.COMMAND_FAILED, self._on_terminal_command_failed)


    def _register_ui_events(self):
        event_bus.subscribe(Events.UI.NAVIGATION_REQUESTED, self._on_navigation_requested)
        event_bus.subscribe(Events.UI.SIDEBAR_TOGGLE_REQUESTED, self._on_sidebar_toggle_requested)

    # -----------------------------
    # HARDWARE Events
    # -----------------------------
    def _on_hardware_refresh_requested(self):
        def on_done(boards):
            ports = [b.port for b in boards]

            self.hardware_ctx = HardwareContext(
                boards=boards,
                ports=ports,
                selected_board=None,
                selected_port=None,
                selected_fqbn=None,
                connected=bool(boards),
                error=None,
            )
            event_bus.emit(HW.BOARDS_DETECTED, boards=boards)

        arduino_service.detect_hardware(on_done=on_done)

    def _on_board_selected(self, port: str):
        board = next(
            (b for b in self.hardware_ctx.boards if b.port == port),
            None
        )

        if not board or not board.fqbn:
            event_bus.emit(HW.HARDWARE_ERROR, error="Selected board not found")
            return

        self.hardware_ctx = HardwareContext(
            **{
                **self.hardware_ctx.__dict__,
                "selected_board": board.name,
                "selected_port": board.port,
                "selected_fqbn": board.fqbn,
            }
        )
        event_bus.emit(
            HW.SELECTION_CHANGED, 
            board=board.name,
            port=board.port,
            fqbn=board.fqbn,
        )

    def _on_port_selected(self, port: str):
        self.hardware_ctx = HardwareContext(
            **{
                **self.hardware_ctx.__dict__,
                "selected_port": port,
            }
        )
        event_bus.emit(HW.SELECTION_CHANGED, port=port)


    # -----------------------------
    # SERIAL Requests (UI → AppController → SerialService)
    # -----------------------------
    def _on_serial_open_requested(self, port: str, baudrate: int = 115200):
        self.serial_service.connect(port=port, baudrate=baudrate)

    def _on_serial_close_requested(self):
        self.serial_service.disconnect()

    def _on_serial_write_requested(self, data: str):
        self.serial_service.write(data)

    # -----------------------------
    # SERIAL - Facts (SerialService → AppController → Context/UI)
    # -----------------------------
    def _on_serial_opened(self, port: str, baudrate: int):
        self.serial_ctx = SerialContext(
            is_open=True,
            port=port,
            baudrate=baudrate,
            busy=False,
            last_error=None,
        )
        event_bus.emit(Serial.OPENED, context=self.serial_ctx)
        
    def _on_serial_closed(self):
        self.serial_ctx = SerialContext(
            is_open=False,
            port=None,
            baudrate=None,
            busy=False,
            last_error=None,
        )
        event_bus.emit(Serial.CLOSED, context=self.serial_ctx)
        
    def _on_serial_busy(self):
        self.serial_ctx = SerialContext(
            **{**self.serial_ctx.__dict__, "busy":True}
        )
        event_bus.emit(Serial.BUSY, context=self.serial_ctx)

    def _on_serial_data_received(self, data: str):
        event_bus.emit(Serial.DATA_RECEIVED, data=data)

    def _on_serial_write_ack(self, data: str):
        logger.debug(f"Serial write acknowledged: {data}")

    def _on_serial_error(self, message: str):
        self.serial_ctx = SerialContext(
            **{**self.serial_ctx.__dict__, "last_error": message}
        )
        event_bus.emit(Serial.SERIAL_ERROR, context=self.serial_ctx)


    # -----------------------------
    # BUILD — Compile
    # -----------------------------
    def _on_build_compile_requested(self):
        if not self.hardware_ctx.selected_fqbn:   
            event_bus.emit(Build.BUILD_FAILED, error="No board selected")
            return
        
        if self.build_ctx.compiling or self.build_ctx.uploading:
            return

        self.build_ctx = BuildContext(
            compiling=True,
            uploading=False,
            progress=0,
            last_error=None,
        )
        event_bus.emit(Build.BUILD_STARTED)

        fqbn = self.hardware_ctx.selected_fqbn
        if not fqbn:
            self.build_ctx = BuildContext(
                compiling=False,
                uploading=False,
                progress=None,
                last_error="No board selected",
            )
            event_bus.emit(Build.BUILD_FAILED, error=self.build_ctx.last_error)
            return
        
        sketch = self.project_folder

        def on_output(line: str):
            progress = self._parse_compile_progress(line)
            if progress is not None:
                self.build_ctx = BuildContext(
                    **{**self.build_ctx.__dict__, "progress": progress}
                )
                event_bus.emit(Build.BUILD_PROGRESS, progress=progress)

        def on_done(result):
            if result.success:
                self.build_ctx = BuildContext(
                    compiling=False,
                    uploading=False,
                    progress=100,
                    last_error=None,
                )
                event_bus.emit(Build.BUILD_SUCCEEDED)
            else:
                self.build_ctx = BuildContext(
                    compiling=False,
                    uploading=False,
                    progress=None,
                    last_error=result.error.message if result.error else "Unknown error",
                )
                event_bus.emit(Build.BUILD_FAILED, error=self.build_ctx.last_error)

        arduino_service.compile_sketch(
            sketch_path=sketch,
            fqbn=fqbn,
            on_output=on_output,
            on_done=on_done,
        )

    # -----------------------------
    # BUILD — Upload
    # -----------------------------
    def _on_build_upload_requested(self):
        if not self.hardware_ctx.selected_fqbn or not self.hardware_ctx.selected_port:
            event_bus.emit(Build.UPLOAD_FAILED, error="No board or port selected")
            return

        if self.build_ctx.compiling or self.build_ctx.uploading:
            return

        port = self.hardware_ctx.selected_port
        if not port:
            event_bus.emit(Build.UPLOAD_FAILED, error="No serial port selected")
            return

        self.build_ctx = BuildContext(
            compiling=False,
            uploading=True,
            progress=0,
            last_error=None,
        )
        event_bus.emit(Build.UPLOAD_STARTED)

        fqbn = self.hardware_ctx.selected_fqbn
        if not fqbn:
            event_bus.emit(Build.UPLOAD_FAILED, error=self.build_ctx.last_error)
            return
    
        sketch = self.project_folder

        def on_output(line: str):
            progress = self._parse_upload_progress(line)
            if progress is not None:
                self.build_ctx = BuildContext(
                    **{**self.build_ctx.__dict__, "progress": progress}
                )
                event_bus.emit(Build.BUILD_PROGRESS, progress=progress)

        def on_done(result):
            if result.success:
                self.build_ctx = BuildContext(
                    compiling=False,
                    uploading=False,
                    progress=100,
                    last_error=None,
                )
                event_bus.emit(Build.UPLOAD_SUCCEEDED)
            else:
                self.build_ctx = BuildContext(
                    compiling=False,
                    uploading=False,
                    progress=None,
                    last_error=result.error.message if result.error else "Unknown error",
                )
                event_bus.emit(Build.UPLOAD_FAILED, error=self.build_ctx.last_error)

        arduino_service.upload_sketch(
            sketch_path=sketch,
            fqbn=fqbn,
            port=port,
            on_output=on_output,
            on_done=on_done,
        )


    def _on_build_abort_requested(self):
        # Future-safe hook (arduino-cli does not support abort yet)
        logger.warning("Build abort requested — not supported yet")

    # -----------------------------
    # Terminal (independent)
    # -----------------------------
    def _on_terminal_command_requested(self, command: str):
        self.terminal.send_command(command)

    def _on_terminal_output_received(self, line: str):
        pass  # or update state only

    def _on_terminal_command_finished(self):
        logger.info("Terminal command finished")

    def _on_terminal_command_failed(self, message: str | None = None, line: str | None = None):
        logger.error(message or line or "Terminal error")

    # -----------------------------
    # Progress parsing (Arduino CLI)
    # -----------------------------
    def _parse_compile_progress(self, line: str) -> Optional[int]:
        if "Sketch uses" in line:
            return 90
        if "Done compiling" in line or "Compiled" in line:
            return 100
        return None

    def _parse_upload_progress(self, line: str) -> Optional[int]:
        if "Writing" in line:
            return 50
        if "Hard resetting" in line:
            return 100
        return None

    # ============================================================
    # UI policy
    # ============================================================

    def _on_navigation_requested(self, target: str):
        if self._is_navigation_allowed(target):
            app_state.set(StateKeys.ACTIVE_VIEW, target, owner="AppController")
            event_bus.emit(Events.UI.NAVIGATION_ALLOWED, target=target)
        else:
            event_bus.emit(
                Events.UI.NAVIGATION_DENIED,
                target=target,
                reason="Navigation blocked by policy",
            )

    def _on_sidebar_toggle_requested(self):
        current = app_state.get(StateKeys.SIDEBAR_COLLAPSED, True)
        new_value = not current

        app_state.set(StateKeys.SIDEBAR_COLLAPSED, new_value, owner="AppController")
        event_bus.emit(Events.UI.SIDEBAR_STATE_CHANGED, collapsed=new_value)

    # ============================================================
    # Navigation rules
    # ============================================================

    def _is_navigation_allowed(self, target: str) -> bool:
        return target in {
            "Home",
            "Simulation",
            "Code Editor",
            "Measurements",
            "Data & Analysis",
            "Notifications",
            "Settings",
        }
