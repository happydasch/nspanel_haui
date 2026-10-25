from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPResponse, NotifEvent, SysPanelKey
from ..mapping.icons import DEFAULT_NOTIF_ICON_FALLBACK, DEFAULT_NOTIF_ICONS
from ..utils.notification_blinker import NotificationBlinker


class Notification(NamedTuple):
    """A queued notification (a tuple, so index access and equality still work)."""

    title: str
    message: str
    icon: str
    timeout: int
    persistent: bool
    notif_type: str
    force_show: bool = False
    require_ack: bool = False
    text_size: str | int = "auto"


class HAUINotificationController(HAUIBase):
    """Notification Controller

    Provides functionality for notifications.
    Also hosts a shared NotificationBlinker so every page does not
    need its own 1-second timer.
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
        self._notifications: list[Notification] = []
        self._blinker = NotificationBlinker()
        self._blinker_refresh_fn: Callable[[], None] | None = None
        # id(notification) -> timer handle for expiry
        self._expiry_timers: dict[int, str] = {}
        # id(notification) -> timer handle for the require_ack re-alert loop
        self._alert_timers: dict[int, str] = {}
        # Items of the notification list popup. Updated in place: closing a
        # notification popup re-renders the list from the kwargs it was opened with.
        self._list_items: list[dict[str, str]] = []

    def stop_part(self) -> None:
        """Stops the part: a pending blink timer must not outlive the app."""
        self._blinker.stop()

    def send_notification(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        timeout: int = 0,
        persistent: bool = False,
        notif_type: str = "info",
        force_show: bool = False,
        require_ack: bool = False,
        text_size: str | int = "auto",
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
        require_ack: bool, optional
            When True the notification cannot time out and re-opens its popup
            periodically until the user presses "Acknowledge" (implies
            persistent sound).  Guaranteed-attention notifications for alarms
            and similar.
        text_size: str or int, optional
            Popup body text size: "auto" (default; chosen from the message
            length) or a font size 1-3.
        """

        self.log(f"Sending notification: title={title!r} persistent={persistent} type={notif_type}")
        self.add_notification(
            title,
            message,
            icon,
            timeout,
            persistent,
            notif_type,
            force_show,
            require_ack,
            text_size,
        )

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
        require_ack: bool = False,
        text_size: str | int = "auto",
    ) -> Notification:
        # A repeat replaces the queued copy so it alerts again and restarts its timeout.
        for existing in self._notifications:
            if existing.title == title and existing.message == message:
                self.log(f"Replacing queued notification: {title!r}")
                self._remove(existing)
                break

        # Max queue size: drop oldest if at limit
        if len(self._notifications) >= self.MAX_QUEUE_SIZE:
            oldest = self._notifications[0]
            self.log(f"Notification queue full, dropping oldest: {oldest.title!r}")
            self._remove(oldest)

        # An ack-required notification must not silently expire while it is
        # unacknowledged: it ignores any timeout and loops the sound.
        if require_ack:
            persistent = True
            timeout = 0

        # Give every notification a visible icon when the caller does not
        # supply one.  Without this the popup renders without an icon and the
        # notification looks like a plain text box.
        if not icon:
            icon = DEFAULT_NOTIF_ICONS.get(notif_type, DEFAULT_NOTIF_ICON_FALLBACK)

        notification = Notification(
            title,
            message,
            icon,
            timeout,
            persistent,
            notif_type,
            force_show,
            require_ack,
            text_size,
        )
        self._notifications.append(notification)
        self._refresh_list_items()
        event = HAUIEvent(NotifEvent.NOTIF_ADD, value=notification)
        self.app.callback_event(event)
        self._fire_notification_event("added", notification)

        # Schedule expiry if timeout > 0
        if timeout > 0:
            notif_id = id(notification)
            handle = self.app.run_in(lambda _data: self._expire_notification(notif_id), timeout)
            self._expiry_timers[notif_id] = handle

        # Ack-required notifications re-open their popup until acknowledged.
        if require_ack:
            self._schedule_re_alert(notification)

        if force_show:
            self.open_notifications()

        return notification

    def remove_notification(self, notification: Notification) -> bool:
        # Match by value but remove the stored instance: expiry timers are keyed by its id().
        for stored in self._notifications:
            if stored == notification:
                self._remove(stored)
                return True
        return False

    def clear_notifications(self) -> None:
        # Cancel all expiry timers
        for handle in self._expiry_timers.values():
            self.app.cancel_timer(handle)
        self._expiry_timers.clear()
        # Cancel all re-alert loops
        for handle in self._alert_timers.values():
            self.app.cancel_timer(handle)
        self._alert_timers.clear()
        self._notifications = []
        self._refresh_list_items()
        event = HAUIEvent(NotifEvent.NOTIF_CLEAR, value=None)
        self.app.callback_event(event)

    def _remove(self, notification: Notification) -> None:
        """Remove a queued notification, given the stored instance."""
        self._cancel_expiry(notification)
        self._cancel_re_alert(notification)
        self._notifications.remove(notification)
        self._refresh_list_items()
        if not self._notifications:
            self._blinker.mark_read()
        event = HAUIEvent(NotifEvent.NOTIF_REMOVE, value=notification)
        self.app.callback_event(event)
        self._fire_notification_event("removed", notification)

    def get_notifications(self) -> list:
        return self._notifications.copy()

    def has_notifications(self) -> bool:
        return len(self._notifications) > 0

    def has_persistent_notifications(self) -> bool:
        return any(n.persistent for n in self._notifications)

    # ------------------------------------------------------------------
    # Notification expiry
    # ------------------------------------------------------------------

    def _cancel_expiry(self, notification: Notification) -> None:
        """Cancel the expiry timer for a notification, if any."""
        notif_id = id(notification)
        handle = self._expiry_timers.pop(notif_id, None)
        if handle is not None:
            self.app.cancel_timer(handle)

    def _expire_notification(self, notification_id: int) -> None:
        """Called via app.run_in when a notification's timeout expires."""
        self._expiry_timers.pop(notification_id, None)
        for n in self._notifications:
            if id(n) == notification_id:
                self.log(f"Notification expired: {n.title!r}")
                self._remove(n)
                return

    # ------------------------------------------------------------------
    # Ack-required re-alert loop
    # ------------------------------------------------------------------

    def _re_alert_interval(self) -> int:
        """Seconds between re-alert popups for unacknowledged notifications."""
        interval = self.get("re_alert_interval", 60)
        try:
            return max(5, int(interval))
        except (TypeError, ValueError):
            return 60

    def _schedule_re_alert(self, notification: Notification) -> None:
        """Arm the periodic re-alert that re-opens the popup until acknowledged."""
        notif_id = id(notification)
        handle = self.app.run_in(
            lambda _data: self._re_alert(notif_id), self._re_alert_interval()
        )
        self._alert_timers[notif_id] = handle

    def _cancel_re_alert(self, notification: Notification) -> None:
        """Cancel the re-alert loop for a notification, if any."""
        handle = self._alert_timers.pop(id(notification), None)
        if handle is not None:
            self.app.cancel_timer(handle)

    def _re_alert(self, notification_id: int) -> None:
        """Re-open the popup of an unacknowledged notification.

        Re-arms itself as long as the notification is still queued. While the
        idle page is active, the popup is not forced open; the loop keeps
        running and re-alerts as soon as the user returns to a real panel.
        """
        self._alert_timers.pop(notification_id, None)
        # While the idle page (automatic page switching) is shown the
        # popup is not forced open; the loop keeps running and re-alerts as
        # soon as the user is back on a real panel.
        navigation = self.app.controller.get("navigation")
        idle_page = navigation.idle_panel_active if navigation is not None else False
        for n in self._notifications:
            if id(n) != notification_id:
                continue
            if n.require_ack and not idle_page:
                self.log(f"Re-alerting unacknowledged notification: {n.title!r}")
                self.open_notification(n)
            # Re-arm regardless so the alert resumes after the user wakes up.
            self._schedule_re_alert(n)
            return

    # ------------------------------------------------------------------
    # Viewing notifications
    # ------------------------------------------------------------------

    def open_notifications(self) -> None:
        """Show the queued notifications and mark them read.

        A single notification opens its popup, several open the list.
        """
        if not self._notifications:
            return
        self._blinker.mark_read()
        if len(self._notifications) == 1:
            self.open_notification(self._notifications[0])
        else:
            self.open_notification_list()

    def open_notification(self, notification: Notification) -> None:
        """Open the popup for one notification, with a button that dismisses it."""
        if notification.require_ack:
            btn_right = self.translate("Acknowledge")
        else:
            btn_right = self.translate("Dismiss")
        self.app.controller["navigation"].open_panel(
            SysPanelKey.POPUP_NOTIFY,
            icon=notification.icon,
            title=notification.title,
            notification=notification.message,
            notif_type=notification.notif_type,
            text_size=notification.text_size,
            btn_right=btn_right,
            button_callback_fnc=lambda _left, _right: self.remove_notification(notification),
            close_on_button=True,
            close_timeout=notification.timeout,
        )

    def open_notification_list(self) -> None:
        """Open the selection page with all pending notifications.

        Each notification is shown as a selectable item.  Tapping one
        opens its detail popup via :meth:`_on_notification_selected`.
        """
        self._refresh_list_items()
        self.app.controller["navigation"].open_panel(
            SysPanelKey.POPUP_SELECT,
            items=self._list_items,
            selection_callback_fnc=self._on_notification_selected,
            close_on_select=False,
            select_mode="full",
        )

    def _refresh_list_items(self) -> None:
        items = []
        for n in self._notifications:
            title = str(n.title) if n.title else ""
            message = str(n.message) if n.message else ""
            # Do not truncate here: the list renderer scrolls/clips the text
            # itself and users reported that long messages were stripped.
            label = f"{title}: {message}" if message else title
            # id() rather than the index: the queue can change while the list is open.
            items.append({"value": str(id(n)), "name": label})
        self._list_items[:] = items

    def _on_notification_selected(self, selected_value: str | None) -> None:
        """Open the detail popup for the selected notification.

        Args:
            selected_value: ``id()`` of the notification as a string. Tapping
                the selected item again passes the same value.
        """
        for n in self._notifications:
            if str(id(n)) == selected_value:
                self.open_notification(n)
                return

    # ------------------------------------------------------------------
    # HA events
    # ------------------------------------------------------------------

    def _fire_notification_event(self, state: str, notification: Notification) -> None:
        """Publish a ``nspanel_haui.notification`` HA event for automations.

        Payload carries the device name and the notification's public fields
        so automations can react (e.g. forward critical alerts off-device,
        log doorbell rings, or reset the queue from a script).
        """
        self.app.fire_event(
            "nspanel_haui.notification",
            {
                "device": self.app.device.get_name(),
                "state": state,
                "title": str(notification.title),
                "message": str(notification.message),
                "icon": notification.icon,
                "notif_type": notification.notif_type,
                "persistent": notification.persistent,
                "require_ack": notification.require_ack,
                "timeout": notification.timeout,
            },
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
            require_ack = notification.get("require_ack", False)
            text_size = notification.get("text_size", "auto")
            self.add_notification(
                title,
                message,
                icon,
                timeout,
                persistent,
                notif_type,
                force_show,
                require_ack,
                text_size,
            )
        # Also forward notification lifecycle events to the shared blinker
        # so pages don't need to handle them individually.
        self._blinker.handle_event(event)
