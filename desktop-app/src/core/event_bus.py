# src/core/event_bus.py
"""
EventBus - thread-safe publish/subscribe system for JUMPER-Z.

Features:
- Singleton pattern via `event_bus` instance at bottom of file
- Thread-safe listener registry (uses threading.Lock)
- Weak references for listeners to avoid memory leaks (works with bound methods)
- Supports synchronous and asynchronous (coroutine) listeners
- Ability to register an asyncio event loop for thread-safe coroutine scheduling
- Utilities: subscribe, subscribe_once, unsubscribe, emit, clear
- Detailed logging on exceptions and debug traces
"""

from __future__ import annotations

import threading
import inspect
import weakref
import asyncio
from typing import Callable, Dict, List, Optional, Any, Final

from src.core.logging_config import get_logger
from src.core.log_events import L

logger = get_logger(__name__)

def _make_weak_ref(callback: Callable) -> weakref.ref | weakref.WeakMethod:
    """Return a weak reference for plain functions or bound methods."""
    return weakref.WeakMethod(callback) if inspect.ismethod(callback) else weakref.ref(callback)


def _deref(ref):
    """Return the referenced object from a weakref (or None)."""
    try:
        return ref()
    except Exception:
        return None


class EventBus:
    """
    Thread-safe Publish/Subscribe system for JUMPER-Z.
    Uses weak references to prevent UI memory leaks.
    """
    def __init__(self):
        self._listeners: Dict[str, List[weakref.ref]] = {}
        self._lock: Final[threading.Lock] = threading.Lock()
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None

    def subscribe(self, event_name: str, callback: Callable) -> None:
        """
        Register a listener for an event.

        The callback can be a normal function or an async function (coroutine function).
        A weak reference is held so that subscriber objects can be garbage collected.
        """
        if not callable(callback):
            raise ValueError(f"EventBus: {callback} is not callable")

        ref = _make_weak_ref(callback)
        with self._lock:
            self._listeners.setdefault(event_name, []).append(ref)

        logger.debug("EventBus: subscribed %r to '%s'", callback, event_name,
                     extra={"event_id": L.CORE.EVENT_SUBSCRIBED})


    def subscribe_once(self, event_name: str, callback: Callable) -> None:
        """
        Subscribe a callback that will be removed after its first successful invocation.
        Professional implementation for one-shot hardware responses.
        """
        # Wrap the callback
        def wrapper(*args: Any, **kwargs: Any) -> None:
            try:
                # Execute the original logic
                callback(*args, **kwargs)
            finally:
                # Ensure we clean up even if the callback crashed
                self.unsubscribe(event_name, wrapper)

        self.subscribe(event_name, wrapper)

        logger.debug("One-shot subscription for '%s'", event_name, 
                     extra={"event_id": L.CORE.EVENT_SUBSCRIBED_ONCE})

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        """Unsubscribe a listener. Handles dead refs automatically."""
        with self._lock:
            if event_name not in self._listeners:
                return
            
            # Filter out the specific callback and any dead references
            new_list = []
            for ref in self._listeners[event_name]:
                obj = ref()
                if obj is not None and obj != callback:
                    new_list.append(ref)
            
            if new_list:
                self._listeners[event_name] = new_list
            else:
                del self._listeners[event_name]

        logger.debug("Unsubscribed %r from '%s'", callback, event_name,
                      extra={"event_id": L.CORE.EVENT_UNSUBSCRIBED})


    def clear(self) -> None:
        """Remove all listeners for all events."""
        with self._lock:
            self._listeners.clear()
        logger.debug("EventBus: cleared all listeners", extra={"event_id": L.CORE.EVENT_CLEARED})

    # ----------------------------
    # Async loop registration
    # ----------------------------
    def register_async_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        Register an asyncio event loop (usually the application's main loop)
        so coroutine listeners can be scheduled safely from other threads.

        Call from the main asyncio-running thread:
            event_bus.register_async_loop(asyncio.get_event_loop())
        """
        self._async_loop = loop
        logger.debug("EventBus: registered async loop %r", loop,
                     extra={"event_id": L.CORE.EVENT_LOOP_REGISTERED})


    def emit(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        """
        Broadcast event.
        - Sync listeners run on emitter thread.
        - Async listeners are scheduled on the registered loop.
        """
        to_call = []
        
        with self._lock:
            if event_name not in self._listeners:
                logger.debug("Emit '%s' - 0 listeners found.", event_name, 
                             extra={"event_id": L.CORE.EVENT_MISSING_LISTENER})
                return
            
            refs = self._listeners[event_name]
            still_alive = []
            for r in refs:
                if (obj := r()) is not None:
                    to_call.append(obj)
                    still_alive.append(r)
            
            self._listeners[event_name] = still_alive

        if not to_call:
            return
        
        logger.debug("Emitting '%s' to %d listeners", event_name, len(to_call),
                     extra={"event_id": L.CORE.EVENT_EMITTED})

        for callback in to_call:
            try:
                if inspect.iscoroutinefunction(callback):
                    self._schedule_async(callback(*args, **kwargs))
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error("Callback error on '%s': %s", event_name, e, 
                             extra={"event_id": L.CORE.EVENT_HANDLER_ERROR})
                

    # ----------------------------
    # Async Scheduling Logic (Internal helper)
    # ----------------------------
    def _schedule_async(self, coro) -> None:
        """
        Schedules a coroutine on the registered event loop.
        This is the bridge between Threads and Asyncio.
        """
        if self._async_loop and self._async_loop.is_running():
            try:
                # Thread-safe way to push work to the Async loop from ANY thread
                asyncio.run_coroutine_threadsafe(coro, self._async_loop)
            except Exception as e:
                logger.error("EventBus: Failed to schedule coroutine: %s", e, 
                             extra={"event_id": L.CORE.EVENT_HANDLER_ERROR})
        else:
            # Fallback: If no loop is registered, we try the current thread's loop
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(coro)
            except RuntimeError:
                # CRITICAL: If we get here, the app is misconfigured. 
                # We log it as a warning instead of spawning uncontrolled threads.
                logger.warning("EventBus: No async loop registered. Dropping async event.", 
                               extra={"event_id": L.CORE.EVENT_HANDLER_ERROR})

    # ----------------------------
    # Introspection (Debugging)
    # ----------------------------
    def get_listeners(self, event_name: str) -> List[Callable]:
        """Returns a list of currently active (live) listeners for an event."""
        with self._lock:
            if event_name not in self._listeners:
                return []
            
            # Extract live objects from weakrefs
            return [obj for r in self._listeners[event_name] if (obj := r()) is not None]

    def get_event_names(self) -> List[str]:
        """Returns all registered event topics."""
        with self._lock:
            return list(self._listeners.keys())

# Global singleton instance
event_bus: Final[EventBus] = EventBus()
