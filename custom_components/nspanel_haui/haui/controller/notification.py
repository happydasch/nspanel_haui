from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from ...nspanel_haui import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import ESPResponse, NotifEvent, NotifType, SysPanelKey
from ..mapping.icons import DEFAULT_NOTIF_ICON_FALLBACK, DEFAULT_NOTIF_ICONS
from ..utils.notification_blinker import NotificationBlinker


class Notification(NamedTuple):
    """A queued notification (a tuple, so index access and equality still work)."""

    title: str
    message: str
    icon: str
    persistent: bool
    notif_type: str
    force_show: bool = False
    text_size: str | int = "auto"


class HAUINotificationController(HAUIBase):
    """Notification Controller

    Provides functionality for notifications.
    Also hosts a shared NotificationBlinker so every page does not
    need its own 1-second timer.
    """

    MAX_QUEUE_SIZE = 50
    # Seconds between forced re-opens of a persistent notification's popup.
    # A persistent notification stays in the queue until dismissed; while it
    # is queued, this loop brings its popup back to the screen if the user
    # navigated away, so the alert is never silently lost.
    PERSISTENT_ALERT_INTERVAL = 60
    # Severities allowed to interrupt the idle/screensaver page when a
    # persistent alert re-opens its popup.  Everything else waits for the
    # user to return to a real panel: a non-critical alert must not flash the
    # bedroom screen every PERSISTENT_ALERT_INTERVAL seconds all night.
    FORCE_OVER_IDLE_TYPES = frozenset({NotifType.CRITICAL})

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any]):
        """Initialize for notification controlller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f"Creating Notification Controller with config: {config}", level="DEBUG")
        self._notifications: list[Notification] = []
        self._blinker = NotificationBlinker()
        self._blinker_refresh_fn: Callable[[], None] | None = None
        # Items of the notification list popup. Updated in place: closing a
        # notification popup re-renders the list from the kwargs it was opened with.
        self._list_items: list[dict[str, str]] = []
        # id() of the notification whose popup is currently displayed, or None.
        # Lets the close path know whether the closed popup was a queued
        # notification, so the queue player can move on to the next one.
        self._open_popup_notif_id: str | None = None
        # Handle of a deferred "show next queued notification" timer.
        self._advance_handle: str | None = None
        # Periodic re-alert timers for persistent notifications, keyed by id().
        self._persistent_alert_handles: dict[str, str] = {}
        # Stable reference to the notification selection callback: bound
        # methods compare by identity, and each attribute access creates a
        # new object, so a stored bound method must be compared against the
        # exact object it was stored as.
        self._notification_selection_callback = self._on_notification_selected

    def stop_part(self) -> None:
        """Stops the part: pending timers must not outlive the app."""
        self._blinker.stop()
        if self._advance_handle is not None:
            self.app.cancel_timer(self._advance_handle)
            self._advance_handle = None
        for handle in self._persistent_alert_handles.values():
            self.app.cancel_timer(handle)
        self._persistent_alert_handles.clear()

    def send_notification(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        persistent: bool = False,
        notif_type: str = NotifType.INFO,
        force_show: bool = False,
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
        persistent: bool, optional
            When True the notification sound loops and its popup re-opens
            periodically until the notification is dismissed.
        notif_type: str, optional
            Severity type: "info", "warning", or "critical".
        force_show: bool, optional
            When True, opens the notification panel immediately.
        text_size: str or int, optional
            Popup body text size: "auto" (default; chosen from the message
            length) or a font size 1-3.
        """

        self.log(f"Sending notification: title={title!r} persistent={persistent} type={notif_type}")
        self.add_notification(
            title,
            message,
            icon,
            persistent,
            notif_type,
            force_show,
            text_size,
        )

    # notifications

    def add_notification(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        persistent: bool = False,
        notif_type: str = NotifType.INFO,
        force_show: bool = False,
        text_size: str | int = "auto",
    ) -> Notification:
        # A repeat replaces the queued copy so it alerts again.
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

        # Give every notification a visible icon when the caller does not
        # supply one.  Without this the popup renders without an icon and the
        # notification looks like a plain text box.
        if not icon:
            icon = DEFAULT_NOTIF_ICONS.get(notif_type, DEFAULT_NOTIF_ICON_FALLBACK)

        notification = Notification(
            title,
            message,
            icon,
            persistent,
            notif_type,
            force_show,
            text_size,
        )
        self._notifications.append(notification)
        self._refresh_list_items()
        # The notification list may be open right now: show the new item as
        # soon as it is queued instead of waiting for the next interaction.
        self._refresh_open_list()
        event = HAUIEvent(NotifEvent.NOTIF_ADD, value=notification)
        self.app.callback_event(event)
        self._fire_notification_event("added", notification)

        # A force-show notification opens immediately — unless a notification
        # popup or list is already on screen.  Stealing an open notification
        # popup would show the new arrival only once and drop the one the
        # user is still reading; instead it waits in the queue and opens when
        # the current one is dismissed.
        if force_show and not self._notification_view_open():
            self.open_notifications()

        # A persistent notification must stay accessible: keep bringing its
        # popup back until the user dismisses it.
        if notification.persistent:
            self._start_persistent_alert(notification)

        return notification

    def _start_persistent_alert(self, notification: Notification) -> None:
        """Re-open a persistent notification's popup until it is dismissed.

        Arms a repeating timer that puts the notification back on screen
        every ``PERSISTENT_ALERT_INTERVAL`` seconds while it stays queued.
        The timer stops itself once the notification leaves the queue (and
        is cancelled eagerly by ``_remove``/``clear_notifications``).
        """
        notif_id = str(id(notification))

        def _re_alert_tick(_data: Any = None) -> None:
            # Dismissed or cleared: stop the loop and drop the handle.
            if not any(str(id(n)) == notif_id for n in self._notifications):
                handle = self._persistent_alert_handles.pop(notif_id, None)
                if handle is not None:
                    self.app.cancel_timer(handle)
                return
            # Never steal an open notification popup or list from the user.
            if self._notification_view_open():
                return
            for n in self._notifications:
                if str(id(n)) == notif_id:
                    # While the idle/screensaver page is shown, only alerts in
                    # FORCE_OVER_IDLE_TYPES may interrupt it.  Other persistent
                    # alerts stay queued and re-appear as soon as the user
                    # returns to a real panel; the timer keeps running, so the
                    # "never silently lost" guarantee still holds.
                    if self._idle_page_active() and n.notif_type not in self.FORCE_OVER_IDLE_TYPES:
                        return
                    self.open_notification(n)
                    break

        handle = self.app.run_every(
            _re_alert_tick,
            "now+1",
            self.PERSISTENT_ALERT_INTERVAL,
        )
        self._persistent_alert_handles[notif_id] = handle

    def remove_notification(self, notification: Notification) -> bool:
        # Match by value but remove the stored instance.
        for stored in self._notifications:
            if stored == notification:
                self._remove(stored)
                return True
        return False

    def clear_notifications(self) -> None:
        # A pending queue advance must not fire after a clear.
        if self._advance_handle is not None:
            self.app.cancel_timer(self._advance_handle)
            self._advance_handle = None
        # Stop every periodic re-alert loop along with its notification.
        for handle in self._persistent_alert_handles.values():
            self.app.cancel_timer(handle)
        self._persistent_alert_handles.clear()
        self._open_popup_notif_id = None
        notifications = self._notifications.copy()
        self._notifications = []
        self._refresh_list_items()
        for notification in notifications:
            self._fire_notification_event("removed", notification)
        event = HAUIEvent(NotifEvent.NOTIF_CLEAR, value=None)
        self.app.callback_event(event)

    def _remove(self, notification: Notification) -> None:
        """Remove a queued notification, given the stored instance."""
        # Stop the periodic re-alert loop for this notification, if any.
        handle = self._persistent_alert_handles.pop(str(id(notification)), None)
        if handle is not None:
            self.app.cancel_timer(handle)
        self._notifications.remove(notification)
        self._refresh_list_items()
        # If the notification list is displayed, drop the removed item and
        # close the list when nothing is left.
        self._refresh_open_list()
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
        """Open the popup for one notification, with a button that dismisses it.

        The popup carries a ``notif_id`` marker so other uses of the same
        Nextion page are never treated as notification popups, and a close
        callback that continues the queue.  When this popup closes and its
        notification is no longer queued (dismissed or expired), the next
        queued notification opens in its place.
        """
        notif_id = str(id(notification))
        btn_right = self.translate("Dismiss")
        self.app.controller["navigation"].open_panel(
            SysPanelKey.POPUP_NOTIFY,
            icon=notification.icon,
            title=notification.title,
            notification=notification.message,
            notif_type=notification.notif_type,
            text_size=notification.text_size,
            notif_id=notif_id,
            btn_right=btn_right,
            button_callback_fnc=lambda _left, _right: self.remove_notification(notification),
            close_on_button=True,
            close_callback_fnc=lambda: self._on_notification_popup_closed(notif_id),
        )
        self._open_popup_notif_id = notif_id

    def open_notification_list(self) -> None:
        """Open the selection page with all pending notifications.

        Each notification is shown as a selectable item.  Tapping one
        opens its detail popup via :meth:`_on_notification_selected`.
        """
        self._open_popup_notif_id = None
        self._refresh_list_items()
        self.app.controller["navigation"].open_panel(
            SysPanelKey.POPUP_SELECT,
            items=self._list_items,
            selection_callback_fnc=self._notification_selection_callback,
            close_on_select=False,
            select_mode="full",
        )

    # ------------------------------------------------------------------
    # Queue player
    # ------------------------------------------------------------------

    def _notification_view_open(self) -> bool:
        """Whether a notification popup or the notification list is displayed.

        Used by :meth:`add_notification` to stop force-show notifications
        from ripping an open notification popup (or list) away from the
        user: they wait in the queue instead and are shown when the current
        popup closes.
        """
        navigation = self.app.controller.get("navigation")
        panel = navigation.get_current_panel() if navigation is not None else None
        return panel is not None and self._is_notification_view(panel)

    def _idle_page_active(self) -> bool:
        """Whether the idle (screensaver) page is currently shown.

        Used by the persistent re-alert loop to decide whether it may
        interrupt what the user is looking at.  The device is the single
        authority on the idle (screensaver) state, independent of display
        brightness.
        """
        return bool(self.app.device.sleeping)

    def _is_notification_view(self, panel: Any) -> bool:
        """True when ``panel`` is a popup/list opened by this controller.

        The ``notify`` page is also used for non-queued popups (entity
        unavailable, update notices, timer finished): the ``notif_id`` marker
        distinguishes the queued-notification popups.
        """
        if panel.get_type() == SysPanelKey.POPUP_NOTIFY:
            return str(panel.get("notif_id", "") or "") != ""
        if panel.get_type() == SysPanelKey.POPUP_SELECT:
            return panel.get("selection_callback_fnc") is self._notification_selection_callback
        return False

    def _on_notification_popup_closed(self, notif_id: str) -> None:
        """A notification popup closed; continue the queue if it was consumed.

        The close callback fires whenever the popup page goes away: on the
        Dismiss button and when the user navigates away.  Only
        the former consumed the notification — i.e. removed it from the
        queue — so the queue advance is armed exactly then.  A popup the
        user left alone (its notification is still queued) does not advance.
        """
        self._open_popup_notif_id = None
        if any(str(id(n)) == notif_id for n in self._notifications):
            return
        self._schedule_advance()

    def _schedule_advance(self) -> None:
        """Defer the queue advance until the current navigation settles.

        The close callback runs in the middle of a navigation operation that
        must finish (pushing or popping panels) before the next popup opens.
        """
        if self._advance_handle is None:
            self._advance_handle = self.app.run_in(self._advance_queue, 0)

    def _advance_queue(self, _data: Any = None) -> None:
        """Open the next queued notification, unless a view already shows one."""
        self._advance_handle = None
        if not self._notifications:
            return
        if self._notification_view_open():
            return
        self.open_notification(self._notifications[0])

    def _refresh_open_list(self) -> None:
        """Re-render the notification list if it is currently displayed.

        The list popup displays the shared ``_list_items`` list by
        reference, but only re-renders when it is (re)opened or interacted
        with.  Re-rendering here keeps it truthful while the user looks at
        it.  A list that lost its last notification is closed — an empty
        selection page has no close affordance.
        """
        navigation = self.app.controller.get("navigation")
        if navigation is None:
            return
        panel = navigation.get_current_panel()
        if panel is None or panel.get_type() != SysPanelKey.POPUP_SELECT:
            return
        if panel.get("selection_callback_fnc") is not self._notification_selection_callback:
            return
        if not self._notifications:
            navigation.close_panel()
            return
        if navigation.page is not None:
            navigation.page.refresh_panel()

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
                "id": str(id(notification)),
                "state": state,
                "title": str(notification.title),
                "message": str(notification.message),
                "icon": notification.icon,
                "notif_type": notification.notif_type,
                "persistent": notification.persistent,
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
            persistent = notification.get("persistent", False)
            notif_type = notification.get("notif_type", NotifType.INFO)
            force_show = notification.get("force_show", False)
            text_size = notification.get("text_size", "auto")
            self.add_notification(
                title,
                message,
                icon,
                persistent,
                notif_type,
                force_show,
                text_size,
            )
        # Also forward notification lifecycle events to the shared blinker
        # so pages don't need to handle them individually.
        self._blinker.handle_event(event)
