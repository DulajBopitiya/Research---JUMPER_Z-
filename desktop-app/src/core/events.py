# src/core/events.py

"""
Central event name registry for JUMPER-Z.
Refactored to a unified Nested-Class structure for better IDE autocomplete.
"""

from enum import Enum, unique
from typing import Final


class AppEvents:
    @unique
    class Hardware(str, Enum):
        REFRESH_REQ = "hw.refresh_requested"
        SELECT_BOARD_REQ = "hw.select_board_requested"
        SELECT_PORT_REQ = "hw.select_port_requested"
        BOARDS_DETECTED = "hw.boards_detected"
        PORTS_DETECTED = "hw.ports_detected"
        SELECTION_CHANGED = "hw.selection_changed"
        CONNECTION_LOST = "hw.connection_lost"
        ERROR = "hw.error"

    @unique
    class Build(str, Enum):
        COMPILE_REQ = "build.compile_requested"
        UPLOAD_REQ = "build.upload_requested"
        ABORT_REQ = "build.abort_requested"

        BUILD_STARTED = "build.started"
        BUILD_PROGRESS = "build.progress"
        BUILD_SUCCEEDED = "build.build_succeeded"
        BUILD_FAILED = "build.build_failed"

        UPLOAD_STARTED = "build.upload_started"
        UPLOAD_SUCCEEDED = "build.upload_succeeded"
        UPLOAD_FAILED = "build.upload_failed"

    # ============================================================
    # SERIAL CONTEXT
    # Owner: SerialContext
    # ============================================================

    @unique
    class Serial(str, Enum):
        # Requests (UI → Controller → Service)
        OPEN_REQUESTED = "serial.open_requested"
        CLOSE_REQUESTED = "serial.close_requested"
        WRITE_REQUESTED = "serial.write_requested"

        # Facts (Service → System)
        OPENED = "serial.opened"
        CLOSED = "serial.closed"
        BUSY = "serial.busy"
        AVAILABLE_PORTS = "serial.available_ports"

        DATA_RECEIVED = "serial.data_received"
        SERIAL_WRITE_ACK = "serial.write_acknowledged"

        SERIAL_ERROR = "serial.error"

    # ============================================================
    # TERMINAL (Command Execution, CLI visibility)
    # Owner: TerminalService
    # ============================================================

    @unique
    class Terminal(str, Enum):
        COMMAND_REQ = "terminal.command_requested"

        OUTPUT_RECEIVED = "terminal.output_received"
        COMMAND_FINISHED = "terminal.command_finished"
        COMMAND_FAILED = "terminal.command_failed"

    # ============================================================
    # PROJECT / FILE SYSTEM
    # ============================================================

    @unique
    class Project(str, Enum):
        PROJECT_OPENED = "project.opened"
        PROJECT_CLOSED = "project.closed"

        FILE_OPENED = "project.file_opened"
        FILE_CLOSED = "project.file_closed"

        FILE_SAVED = "project.file_saved"
        FILE_MODIFIED = "project.file_modified"

    # ============================================================
    # UI/ LAYOUT EVENTS
    # ============================================================
    @unique
    class UI(str, Enum):
        THEME_CHANGED = "ui.theme_changed"
        SIDEBAR_TOGGLE_REQUESTED = "ui.sidebar_toggle_requested"  # user requested sidebar toggle
        SIDEBAR_STATE_CHANGED = "ui.sidebar_state_changed"  # sidebar collapsed/expanded

        NAVIGATION_REQUESTED = "ui.navigation_requested"  # user requested navigation
        NAVIGATION_ALLOWED = "ui.navigation_allowed"  # navigation allowed
        NAVIGATION_DENIED = "ui.navigation_denied"

    @unique
    class State(str, Enum):
        STATE_CHANGED = "state.changed"
        STATE_RESET = "state.reset"

    @unique
    class Nav(str, Enum):
        CHANGE_REQ = "nav.change_requested"
        ALLOWED = "nav.allowed"
        DENIED = "nav.denied"

    # ============================================================
    # TASK / BACKGROUND WORKER EVENTS
    # ============================================================
    class Task:
        TASK_STARTED = "task.task_started"
        TASK_COMPLETED = "task.task_completed"
        TASK_FAILED = "task.task_failed"

    # ============================================================
    # PROJECT / FILE EVENTS
    # ============================================================
    class Project:
        COMPILE_REQUESTED = "project.compile_requested"
        UPLOAD_REQUESTED = "project.upload_requested"

        OPENED = "project.opened"
        CLOSED = "project.closed"
        SAVED = "project.saved"
        MODIFIED = "project.modified"

    class CLI:
        OUTPUT = "cli.output"
        DONE = "cli.done"

    # ============================================================
    # SYSTEM / APP EVENTS
    # ============================================================
    class System:
        SHUTDOWN = "system.shutdown"

    # ============================================================
    # Utility functions
    # ============================================================

    """
    Introspection utility.
    Returns a list of every event string defined inside Events.*
    Used for debugging or generating documentation.
    """

    @staticmethod
    def list_all_events_by_group():
        """Return a dictionary of all events grouped by class."""
        result = {}
        for group_name, group_obj in AppEvents.__dict__.items():
            if isinstance(group_obj, type):  # Only classes
                # Only take string constants, skip private/internal names
                result[group_name] = [
                    v
                    for k, v in group_obj.__dict__.items()
                    if not k.startswith("_") and isinstance(v, str)
                ]
        return result

    @staticmethod
    def print_events_table():
        """Print events in a neat tabular format."""
        events = AppEvents.list_all_events_by_group()
        # Find maximum number of rows
        max_rows = max(len(lst) for lst in events.values())

        # Pad shorter lists with empty strings
        for lst in events.values():
            while len(lst) < max_rows:
                lst.append("")

        # Print header
        headers = list(events.keys())
        print("  ".join(f"{h:<20}" for h in headers))
        print("-" * 20 * len(headers))

        # Print rows
        for i in range(max_rows):
            row = [events[h][i] for h in headers]
            print("  ".join(f"{c:<20}" for c in row))


Events: Final[AppEvents] = AppEvents()

HW: Final = Events.Hardware
Build: Final = Events.Build
Serial: Final = Events.Serial
Terminal: Final = Events.Terminal
State: Final = Events.State
Proj: Final = Events.Project
System: Final = Events.System
