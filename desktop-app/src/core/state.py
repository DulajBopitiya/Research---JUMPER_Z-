# src/core/state.py
"""
Thread-safe global application state with EventBus notifications.
Emits Events.State.STATE_CHANGED only when values actually change.

    state_keys.py           → defines WHAT
    state_ownership.py      → defines WHO
    state.py                → enforces HOW
    AppController           → performs mutation
    UI                      → reads only
"""

from __future__ import annotations
import threading
from typing import Any, Dict, Final

from src.core.state_ownership import STATE_OWNERSHIP
from src.core.state_keys import StateKeys
from src.core.event_bus import event_bus
from src.core.events import Events
from src.core.logging_config import get_logger
from src.core.logging_event_registry import CR

from src.core.config import APP_VERSION as CONFIG_APP_VERSION

logger = get_logger(__name__)

class AppState:
    """Thread-safe key/value state store with differential emit."""

    def __init__(self):
        # RLock allows the same thread to acquire the lock multiple times (Reentrant)
        self._lock: Final[threading.RLock] = threading.RLock()
        self._data: Dict[StateKeys, Any] = {}

        # Default values assigned without emitting events
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Sets internal defaults bypassing ownership checks."""
        self._data.update({
            StateKeys.APP_IS_RUNNING: True,
            StateKeys.CURRENT_THEME: "Dark",
            StateKeys.APP_VERSION: CONFIG_APP_VERSION,
        })

    def set(self, key: StateKeys, value: Any, *, owner: str) -> None:
        """Set a value and emit only when changed."""

        expected_owner = STATE_OWNERSHIP.get(key)

        if expected_owner and expected_owner != owner:
            logger.error("State ownership violation: %s tried to set %s owned by %s",
                         owner, key, expected_owner, 
                         extra={"event_id": CR.STATE_VIOLATION})
            return
        
        with self._lock: 
            old_value = self._data.get(key)

            # Avoid unnecessary updates
            if old_value == value:
                return

            self._data[key] = value
            logger.debug("AppState.set: %s = %r (old=%r)", key, value, old_value, 
                         extra={"event_id": CR.STATE_CHANGED})

        # Emit after releasing lock (to avoid deadlocks)
        try:
            event_bus.emit(Events.State.STATE_CHANGED, key=key, value=value, old_value=old_value)
        except Exception:
            logger.exception("AppState: error emitting set for %s", key,
                             extra={"event_id": CR.EVENT_HANDLER_ERROR})

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def delete(self, key: StateKeys, *, owner: str) -> None:
        expected_owner = STATE_OWNERSHIP.get(key)
        if expected_owner and expected_owner != owner and owner != "AppController":
            logger.error("State deletion violation: %s tried to delete %s (owner=%s)",
                owner, key, expected_owner,
                extra={"event_id": CR.STATE_VIOLATION},)
            return
        
        with self._lock:
            existed = key in self._data
            old_value = self._data.get(key)
            if existed:
                del self._data[key]
                logger.debug("AppState.delete: removed %s", key, extra={"event_id": CR.STATE_CHANGED})

        if existed:
            try:
                event_bus.emit(Events.State.STATE_CHANGED, key=key, value=None, old_value=old_value)
            except Exception:
                logger.exception("AppState: error emitting delete for %s", key, extra={"event_id": CR.EVENT_HANDLER_ERROR})

    def clear(self, *, owner: str) -> None:
        if owner != "AppController":
            logger.error("State clear violation: only AppController can clear state (attempt by %s)", 
                         owner, extra={"event_id": CR.STATE_VIOLATION},)
            return
        
        with self._lock:
            self._data.clear()
            logger.debug("AppState.clear: all keys removed", extra={"event_id": CR.STATE_RESET})

        try:
            event_bus.emit(Events.State.STATE_CHANGED, key=None, value=None, old_value=None)
        except Exception:
            logger.exception("AppState: error emitting clear", extra={"event_id": CR.EVENT_HANDLER_ERROR})

    def all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

app_state: Final[AppState] = AppState()
