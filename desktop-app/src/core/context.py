# src/core/context.py

from dataclasses import dataclass, field
from typing import Optional, List, Set

from src.services.arduino_service import BoardInfo

# ----------------------------
# Hardware Context (boards/ports)
# ----------------------------
@dataclass(frozen=True)
class HardwareContext:
    boards: List[BoardInfo]
    ports: List[str]

    selected_board: Optional[str]
    selected_port: Optional[str]
    selected_fqbn: Optional[str]

    connected: bool
    error: Optional[str]

# ----------------------------
# Serial Runtime Context
# ----------------------------
@dataclass(frozen=True)
class SerialContext:
    is_open: bool
    port: Optional[str]
    baudrate: Optional[int]

    busy: bool          # upload / locked
    last_error: Optional[str]

# ----------------------------
# Build Context (compile/upload)
# ----------------------------
@dataclass(frozen=True)
class BuildContext:
    compiling: bool
    uploading: bool

    progress: Optional[int]   # 0–100 or None
    last_error: Optional[str]
    
# ----------------------------
# Editor Context (files/tabs)
# ----------------------------
@dataclass(frozen=True)
class EditorContext:
    open_files: List[str] = field(default_factory=list)
    active_file: Optional[str] = None
    dirty_files: Set[str] = field(default_factory=set)
