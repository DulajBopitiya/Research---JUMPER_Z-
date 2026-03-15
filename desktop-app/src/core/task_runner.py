# src/core/task_runner.py
"""
Threaded background task runner for JP PLATFORM.
- Runs functions asynchronously in threads
- Reports completion or errors via EventBus
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from src.core.event_bus import event_bus
from src.core.events import Events
from src.core.logging_config import get_logger
from src.core.log_events import L

logger = get_logger(__name__)

class TaskRunner:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()

    def submit(self, fn, *args, **kwargs):
        """
        Submit a task to run in the background.
        Emits:
            - Events.Task.STARTED   → immediately after submission
            - Events.Task.TASK_COMPLETED → on success
            - Events.Task.TASK_FAILED    → on exception
        """
        # Submit the task to the executor
        future = self.executor.submit(fn, *args, **kwargs)

        # Emit STARTED immediately after submission
        event_bus.emit(Events.Task.TASK_STARTED, fn=fn, args=args, kwargs=kwargs)
        logger.debug("TaskRunner: Task %r submitted and started", fn, 
                     extra={"event_id": L.CORE.TASK_STARTED})

        # Callback to handle completion/failure
        def callback(fut):
            try:
                result = fut.result()   # will raise exception if task failed
                event_bus.emit(Events.Task.TASK_COMPLETED, fn=fn, result=result)
                logger.info("TaskRunner: Task %r completed successfully with result %r", fn, result,
                            extra={"event_id": L.CORE.TASK_COMPLETED})
            except Exception as e:
                event_bus.emit(Events.Task.TASK_FAILED, fn=fn, error=e)
                logger.exception("TaskRunner: Task %r failed with error %s", fn, e,
                                 extra={"event_id": L.CORE.TASK_FAILED})

        future.add_done_callback(callback)
        return future

    def shutdown(self, wait=True):
        self.executor.shutdown(wait=wait)
        logger.info("TaskRunner: executor shutdown complete", 
                    extra={"event_id": L.CORE.TASK_COMPLETED})


# Singleton instance
task_runner = TaskRunner()
