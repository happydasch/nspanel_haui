from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPResponse, NotifEvent


class HAUINotificationController(HAUIBase):
    """Notification Controller

    Provides functionality for notifications.
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
