# src/ui/navigation/router.py

from src.core.event_bus import event_bus
from src.core.events import Events
from src.core.logging_config import get_logger
from src.core.log_events import L

logger = get_logger(__name__)


class Router:

    def __init__(self, navigation_host):

        self.host = navigation_host

        event_bus.subscribe(Events.UI.NAVIGATION_ALLOWED,self._on_navigation_allowed)
        event_bus.subscribe(Events.UI.NAVIGATION_DENIED, self._on_navigation_denied)

    def _on_navigation_allowed(self, **_):

        from src.core.state import app_state
        from src.core.state_keys import StateKeys

        view = app_state.get(StateKeys.ACTIVE_VIEW)

        if not view:
            return

        logger.info("Navigation allowed to %s", view, extra={"event_id": L.UI.NAVIGATION_ALLOWED})

        self.host.show(view)

    def _on_navigation_denied(self, target: str, reason: str):
        logger.warning("Navigation denied to %s: %s" , target, reason, extra={"event_id": L.UI.NAVIGATION_DENIED})
        