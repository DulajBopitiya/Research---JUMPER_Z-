import subprocess
import threading
import platform

from src.core.event_bus import event_bus
from src.core.events import Terminal


class TerminalService:
    """
    Persistent interactive terminal session.
    Executes shell commands and streams output via events.
    """

    def __init__(self):
        self.process: subprocess.Popen | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------
    # Start terminal session
    # ------------------------------------------------
    def start(self):
        if self.process:
            return  # already running

        shell_cmd = self._detect_shell()

        self.process = subprocess.Popen(
            shell_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Start reader threads
        threading.Thread(
            target=self._read_stdout,
            daemon=True
        ).start()

        threading.Thread(
            target=self._read_stderr,
            daemon=True
        ).start()

    # ------------------------------------------------
    # Send user command
    # ------------------------------------------------
    def send_command(self, command: str):
        with self._lock:
            if not self.process or not self.process.stdin:
                event_bus.emit(
                    Terminal.COMMAND_FAILED,
                    message="Terminal not running"
                )
                return

            try:
                # Echo command like a real terminal
                event_bus.emit(
                    Terminal.OUTPUT_RECEIVED,
                    line=f"> {command}"
                )

                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()

            except Exception as e:
                event_bus.emit(
                    Terminal.COMMAND_FAILED,
                    message=str(e)
                )

    # ------------------------------------------------
    # Stop terminal session
    # ------------------------------------------------
    def stop(self):
        with self._lock:
            if self.process:
                try:
                    self.process.terminate()
                finally:
                    self.process = None

    # ------------------------------------------------
    # Output readers
    # ------------------------------------------------
    def _read_stdout(self):
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            event_bus.emit(
                Terminal.OUTPUT_RECEIVED,
                line=line.rstrip()
            )

    def _read_stderr(self):
        assert self.process and self.process.stderr
        for line in self.process.stderr:
            # stderr is NOT always failure (Arduino CLI, gcc, etc.)
            event_bus.emit(
                Terminal.OUTPUT_RECEIVED,
                line=line.rstrip()
            )

    # ------------------------------------------------
    # Shell detection
    # ------------------------------------------------
    def _detect_shell(self):
        system = platform.system()

        if system == "Windows":
            # /k = keep shell alive
            return ["cmd.exe", "/k"]

        elif system == "Linux":
            return ["/bin/bash", "-i"]

        elif system == "Darwin":
            return ["/bin/zsh", "-i"]

        else:
            raise RuntimeError("Unsupported OS")
