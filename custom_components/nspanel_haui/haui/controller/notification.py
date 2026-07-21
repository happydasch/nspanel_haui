from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPResponse, NotifEvent, SysPanelKey
from ..utils.notification_blinker import NotificationBlinker


class HAUINotificationController(HAUIBase):
    """Notification Controller

    Provides functionality for notifications.
    Also hosts a shared NotificationBlinker so every page does not
    need its own 1-second timer.

    Notification tuple format:
        (title, message, icon, timeout, persistent, type, force_show)
    """

    MAX_QUEUE_SIZE = 50

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
        # id(notification) -> timer handle for expiry
        self._expiry_timers: dict[int, str] = {}

    def send_notification(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        timeout: int = 0,
        persistent: bool = False,
        notif_type: str = "info",
        force_show: bool = False,
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
        notif_type: str, optional
            Severity type: "info", "warning", or "critical".
        force_show: bool, optional
            When True, opens the notification panel immediately.
        """

        self.log(f"Sending notification: title={title!r} persistent={persistent} type={notif_type}")
        self.add_notification(title, message, icon, timeout, persistent, notif_type, force_show)

    # notifications

    def add_notification(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        timeout: int = 0,
        persistent: bool = False,
        notif_type: str = "info",
        force_show: bool = False,
    ) -> tuple:
        # Deduplication: skip if same (title, message) already exists
        for existing in self._notifications:
            if existing[0] == title and existing[1] == message:
                self.log(f"Notification already queued: {title!r}")
                return existing

        # Max queue size: drop oldest if at limit
        if len(self._notifications) >= self.MAX_QUEUE_SIZE:
            oldest = self._notifications.pop(0)
            self._cancel_expiry(oldest)
            self.log(f"Notification queue full, dropping oldest: {oldest[0]!r}")

        notification = (title, message, icon, timeout, persistent, notif_type, force_show)
        self._notifications.append(notification)
        event = HAUIEvent(NotifEvent.NOTIF_ADD, value=notification)
        self.app.callback_event(event)

        # Schedule expiry if timeout > 0
        if timeout > 0:
            notif_id = id(notification)
            handle = self.app.run_in(lambda _data: self._expire_notification(notif_id), timeout)
            self._expiry_timers[notif_id] = handle

        # Force-show: open the notification panel immediately
        if force_show:
            navigation = self.app.controller.get("navigation")
            if navigation:
                count = len(self._notifications)
                if count == 1:
                    navigation.open_panel(
                        SysPanelKey.POPUP_NOTIFY,
                        icon=icon,
                        title=title,
                        notification=message,
                        close_on_button=True,
                        close_timeout=timeout if timeout > 0 else 0,
                    )
                else:
                    self.open_notification_list()

        return notification

    def remove_notification(self, notification: tuple) -> bool:
        if notification in self._notifications:
            self._cancel_expiry(notification)
            self._notifications.remove(notification)
            event = HAUIEvent(NotifEvent.NOTIF_REMOVE, value=notification)
            self.app.callback_event(event)
            return True
        return False

    def clear_notifications(self) -> None:
        # Cancel all expiry timers
        for handle in self._expiry_timers.values():
            self.app.cancel_timer(handle)
        self._expiry_timers.clear()
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
    # Notification expiry
    # ------------------------------------------------------------------

    def _cancel_expiry(self, notification: tuple) -> None:
        """Cancel the expiry timer for a notification, if any."""
        notif_id = id(notification)
        handle = self._expiry_timers.pop(notif_id, None)
        if handle is not None:
            self.app.cancel_timer(handle)

    def _expire_notification(self, notification_id: int) -> None:
        """Called via app.run_in when a notification's timeout expires."""
        self._expiry_timers.pop(notification_id, None)
        # Find the notification by id and remove it
        for i, n in enumerate(self._notifications):
            if id(n) == notification_id:
                self._notifications.pop(i)
                event = HAUIEvent(NotifEvent.NOTIF_REMOVE, value=n)
                self.app.callback_event(event)
                self.log(f"Notification expired: {n[0]!r}")
                return

    # ------------------------------------------------------------------
    # Open notification selection list (uses SelectPage)
    # ------------------------------------------------------------------

    def open_notification_list(self) -> None:
        """Open the selection page with all pending notifications.

        Each notification is shown as a selectable item.  Tapping one
        opens its detail popup via :meth:`_on_notification_selected`.
        """
        navigation = self.app.controller.get("navigation")
        if not navigation:
            return
        items = []
        for i, n in enumerate(self._notifications):
            title = str(n[0]) if n[0] else ""
            message = str(n[1]) if n[1] else ""
            label = title
            if message:
                label = f"{title}: {message[:40]}"
            items.append({"value": str(i), "name": label[:60]})
        navigation.open_panel(
            SysPanelKey.POPUP_SELECT,
            items=items,
            selection_callback_fnc=self._on_notification_selected,
            close_on_select=False,
            select_mode="full",
        )

    def _on_notification_selected(self, selected_value: str) -> None:
        """Open the detail popup for the selected notification.

        Args:
            selected_value: Stringified index into ``_notifications``.
        """
        try:
            idx = int(selected_value)
        except (ValueError, TypeError):
            return
        if idx < 0 or idx >= len(self._notifications):
            return
        n = self._notifications[idx]
        navigation = self.app.controller.get("navigation")
        if not navigation:
            return
        navigation.open_panel(
            SysPanelKey.POPUP_NOTIFY,
            icon=n[2],
            title=n[0],
            notification=n[1],
            close_on_button=True,
            close_timeout=n[3] if n[3] > 0 else 0,
        )

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
            # Extract the new fields from the JSON data
            title = notification.get("title", "")
            message = notification.get("message", "")
            icon = notification.get("icon", "")
            timeout = notification.get("timeout", 0)
            persistent = notification.get("persistent", False)
            notif_type = notification.get("notif_type", "info")
            force_show = notification.get("force_show", False)
            self.add_notification(title, message, icon, timeout, persistent, notif_type, force_show)
        # Also forward notification lifecycle events to the shared blinker
        # so pages don't need to handle them individually.
        self._blinker.handle_event(event)
