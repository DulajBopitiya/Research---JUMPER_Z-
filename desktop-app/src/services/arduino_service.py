# src/services/arduino_service.py

import subprocess
import threading
import json
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, List, Dict, Any

# ==================================================
# Models
# ==================================================
class ErrorType(Enum):
    CLI_NOT_FOUND = "cli_not_found"
    CORE_NOT_INSTALLED = "core_not_installed"
    BOARD_NOT_FOUND = "board_not_found"
    PORT_NOT_FOUND = "port_not_found"
    COMPILE_FAILED = "compile_failed"
    UPLOAD_FAILED = "upload_failed"
    UNKNOWN = "unknown"

@dataclass
class ArduinoError:
    type: ErrorType
    message: str
    data: Optional[Dict[str, Any]] = None

@dataclass
class ArduinoResult:
    success: bool
    error: Optional[ArduinoError] = None

@dataclass
class BoardInfo:
    port: str
    fqbn: Optional[str]
    name: str

# ==================================================
# Arduino Service Pro
# ==================================================
class ArduinoService:
    """
    Arduino CLI abstraction layer.
    - NO UI
    - NO prompts
    - Structured results only
    """

    def __init__(self, cli_path: Path):
        self.cli_path = str(cli_path)
        self._validate_cli()

    # ------------------------------------------------
    # Validation
    # ------------------------------------------------
    def _validate_cli(self):
        if not Path(self.cli_path).exists():
            raise FileNotFoundError(f"arduino-cli not found at {self.cli_path}")

    # ------------------------------------------------
    # Core runner
    # ------------------------------------------------
    def _run_command(
        self,
        command: List[str],
        on_output: Optional[Callable[[str], None]] = None,
        on_done: Optional[Callable[[int], None]] = None,
    ):
        """Run CLI command in a background thread."""
        def task():
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                for line in process.stdout:
                    if on_output:
                        on_output(line.rstrip())

                exit_code = process.wait()
                if on_done:
                    on_done(exit_code)

            except Exception as e:
                if on_output:
                    on_output(str(e))
                if on_done:
                    on_done(-1)

        threading.Thread(target=task, daemon=True).start()

    # =================================================
    # Compile / Upload
    # =================================================
    def compile_sketch(
        self,
        sketch_path: Path,
        fqbn: str,
        on_output=None,
        on_done: Optional[Callable[[ArduinoResult], None]] = None,
    ):
        cmd = [self.cli_path, "compile", "--fqbn", fqbn, str(sketch_path)]

        def done(exit_code: int):
            if exit_code == 0:
                on_done and on_done(ArduinoResult(success=True))
            else:
                on_done and on_done(
                    ArduinoResult(
                        success=False,
                        error=ArduinoError(
                            type=ErrorType.COMPILE_FAILED,
                            message="Compilation failed",
                            data={"fqbn": fqbn}
                        )
                    )
                )

        self._run_command(cmd, on_output, done)

    def upload_sketch(
        self,
        sketch_path: Path,
        fqbn: str,
        port: str,
        on_output=None,
        on_done: Optional[Callable[[ArduinoResult], None]] = None,
    ):
        cmd = [self.cli_path, "upload", "-p", port, "--fqbn", fqbn, str(sketch_path)]

        def done(exit_code: int):
            if exit_code == 0:
                on_done and on_done(ArduinoResult(success=True))
            else:
                on_done and on_done(
                    ArduinoResult(
                        success=False,
                        error=ArduinoError(
                            type=ErrorType.UPLOAD_FAILED,
                            message="Upload failed",
                            data={"fqbn": fqbn, "port": port}
                        )
                    )
                )

        self._run_command(cmd, on_output, done)

    # =================================================
    # Board detection / FQBN auto
    # =================================================
    def detect_hardware(
        self,
        on_done: Optional[Callable[[List[BoardInfo]], None]] = None,
    ):
        """Detect boards + ports, including FQBN."""
        self.list_connected_boards(on_done=on_done)

    def list_connected_boards(
        self,
        on_done: Optional[Callable[[List[BoardInfo]], None]] = None,
    ):
        """Run `arduino-cli board list --format json` and parse output."""
        cmd = [self.cli_path, "board", "list", "--format", "json"]

        output_lines: List[str] = []

        def collect(line: str):
            output_lines.append(line)

        def done(exit_code: int):
            boards: List[BoardInfo] = []

            if exit_code != 0:
                on_done and on_done([])
                return

            try:
                data = json.loads("\n".join(output_lines))

                for entry in data:
                    port = entry.get("port", {}).get("address")
                    matches = entry.get("matching_boards", [])

                    if not port or not matches:
                        continue

                    board = matches[0]
                    boards.append(
                        BoardInfo(
                            port=port,
                            fqbn=board.get("fqbn"),
                            name=board.get("name", "Unknown Board")
                        )
                    )
            except Exception:
                pass

            on_done and on_done(boards)

        self._run_command(cmd, collect, done)

    # =================================================
    # Core management
    # =================================================
    def list_installed_cores(
        self,
        on_done: Callable[[List[str]], None]
    ):
        cmd = [self.cli_path, "core", "list"]
        cores: List[str] = []

        def parse(line: str):
            if line and not line.startswith("ID"):
                cores.append(line.split()[0])

        def done(_: int):
            on_done(cores)

        self._run_command(cmd, parse, done)

    def install_core(
        self,
        core_name: str,
        on_output=None,
        on_done: Optional[Callable[[ArduinoResult], None]] = None
    ):
        cmd = [self.cli_path, "core", "install", core_name]

        def done(exit_code: int):
            if exit_code == 0:
                on_done and on_done(ArduinoResult(success=True))
            else:
                on_done and on_done(
                    ArduinoResult(
                        success=False,
                        error=ArduinoError(
                            type=ErrorType.CORE_NOT_INSTALLED,
                            message="Core installation failed",
                            data={"core": core_name}
                        )
                    )
                )

        self._run_command(cmd, on_output, done)
