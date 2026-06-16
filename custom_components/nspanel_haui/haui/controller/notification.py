from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPResponse, NotifEvent
from ..utils.notification_blinker import NotificationBlinker


class HAUINotificationController(HAUIBase):
    """Notification Controller

    Provides functionality for notifications.
    Also hosts a shared NotificationBlinker so every page does not
    need its own 1-second timer.
    """

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any]):
        """Initialize for notification controlller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.debug_log(f"Creating Notification Controller with config: {config}")
        self._notifications: list[tuple] = []  # list for notifications
        self._blinker = NotificationBlinker()
        self._blinker_refresh_fn: Callable[[], None] | None = None

    def send_notification(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        timeout: int = 0,
        persistent: bool = False,
    ) -> None:
        """Send a notification to the panel.

        Parameters
        ----------
        title: str
            Title of the notification.
        message: str, optional
            Body text. Can be empty.
        icon: str, optional
            Icon name. Pass empty string to omit.
        timeout: int, optional
            How long the notification should be shown in seconds.
        persistent: bool, optional
            When True the notification sound loops until the notification is dismissed.
        """

        self.log(f"Sending notification: title={title!r} persistent={persistent}")
        self.add_notification(title, message, icon, timeout, persistent)

    # notifications

    def add_notification(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        timeout: int = 0,
        persistent: bool = False,
    ) -> tuple:
        notification = (title, message, icon, timeout, persistent)
        self._notifications.append(notification)
        event = HAUIEvent(NotifEvent.NOTIF_ADD, value=notification)
        self.app.callback_event(event)
        return notification

    def remove_notification(self, notification: tuple) -> bool:
        if notification in self._notifications:
            self._notifications.remove(notification)
            event = HAUIEvent(NotifEvent.NOTIF_REMOVE, value=notification)
            self.app.callback_event(event)
            return True
        return False

    def clear_notifications(self) -> None:
        self._notifications = []
        event = HAUIEvent(NotifEvent.NOTIF_CLEAR, value=None)
        self.app.callback_event(event)

    def get_notifications(self) -> list:
        return self._notifications.copy()

    def has_notifications(self) -> bool:
        return len(self._notifications) > 0

    def has_persistent_notifications(self) -> bool:
        return any(n[4] for n in self._notifications)

    # ------------------------------------------------------------------
    # Shared notification blinker
    # ------------------------------------------------------------------

    @property
    def blinker(self) -> NotificationBlinker:
        """The shared notification blinker instance."""
        return self._blinker

    def set_blinker_callback(self, refresh_fn: Callable[[], None]) -> None:
        """Register a page's notification indicator renderer.

        Called by a page in *start_panel* so the shared blinker
        updates that page's ``t_notif`` component on each blink tick.
        """
        self._blinker_refresh_fn = refresh_fn
        self._blinker.set_callback(self._on_blinker_tick)

    def clear_blinker_callback(self) -> None:
        """Unregister the current page's notification indicator.

        Called by a page in *_stop_panel* so the blinker stops firing.
        """
        self._blinker_refresh_fn = None
        self._blinker.clear_callback()

    def _on_blinker_tick(self) -> None:
        """Dispatch the blink tick to whichever page registered a callback."""
        if self._blinker_refresh_fn is not None:
            self._blinker_refresh_fn()

    # event

    def process_event(self, event: HAUIEvent) -> None:
        """Process events.

        Args:
            event (HAUIEvent): Event
        """
        if event.name == ESPResponse.SEND_NOTIFICATION:
            self.log(f"Send notification: {event.as_str()}")
            notification = event.as_json()
            self.add_notification(**notification)
        # Also forward notification lifecycle events to the shared blinker
        # so pages don't need to handle them individually.
        self._blinker.handle_event(event)
