from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from ...hub.app import NSPanelHAUI

from ..abstract.haui_base import HAUIBase
from ..abstract.haui_event import HAUIEvent
from ..mapping.const import (
    DEFAULT_NOTIFICATION_SOUND,
    SOUND_NAMES,
    ESPResponse,
    NotifEvent,
    PopupPanelKey,
)
from ..utils.notification_blinker import NotificationBlinker


def _normalize_icon_color(
    icon_color: int | str | list[int] | None,
) -> int | str | list[int] | None:
    """Treat an empty colour as "use the popup's theme text colour"."""
    return None if icon_color in (None, "") else icon_color


def _normalize_sound(sound: str) -> str:
    """Resolve a notification sound name; ``""`` and ``"none"`` are silent."""
    value = str(sound or "").strip()
    if value in ("", "none"):
        return ""
    if value not in SOUND_NAMES:
        raise ValueError(f"Unknown notification sound: {sound!r}")
    return value


class Notification(NamedTuple):
    """A queued notification (a tuple, so index access and equality still work)."""

    title: str
    message: str
    icon: str = ""
    persistent: bool = False
    force_show: bool = False
    # Icon colour in any parse_color_value format; None/"" keeps the popup's
    # theme text colour.
    icon_color: int | str | list[int] | None = None
    # Name of an ESPHome play_sound sound; "" is silent.
    sound: str = DEFAULT_NOTIFICATION_SOUND
    text_size: str | int = "auto"
    # Seconds after which the notification auto-dismisses.  None/0 = it stays
    # queued until dismissed (the default; notifications never auto-close).
    timeout: int | None = None
    # Unique id, set by the controller.  It names the notification in the HA
    # event, the editor inbox and the panel's list.  id() was used before, but
    # CPython hands a freed tuple's id straight to the next notification.
    notif_id: str = ""


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

    def __init__(self, app: NSPanelHAUI, config: dict[str, Any]):
        """Initialize for notification controlller.

        Args:
            app (NSPanelHAUI): App
            config (dict): Config for controller
        """
        super().__init__(app, config)
        self.log(f"Creating Notification Controller with config: {config}", level="DEBUG")
        self._notifications: list[Notification] = []
        self._blinker = NotificationBlinker(app, visible_fn=lambda: app.device.display_visible)
        self._blinker_refresh_fn: Callable[[], None] | None = None
        # Items of the notification list popup. Updated in place: closing a
        # notification popup re-renders the list from the kwargs it was opened with.
        self._list_items: list[dict[str, str]] = []
        # notif_id of the notification whose popup is currently displayed, or None.
        # Lets the close path know whether the closed popup was a queued
        # notification, so the queue player can move on to the next one.
        self._open_popup_notif_id: str | None = None
        # Handle of a deferred "show next queued notification" timer.
        self._advance_handle: str | None = None
        # Periodic re-alert timers for persistent notifications, keyed by notif_id.
        self._persistent_alert_handles: dict[str, str] = {}
        # Auto-dismiss timers for notifications with a ``timeout``, keyed by notif_id.
        self._timeout_handles: dict[str, str] = {}
        # Stable reference to the notification selection callback: bound
        # methods compare by identity, and each attribute access creates a
        # new object, so a stored bound method must be compared against the
        # exact object it was stored as.
        self._notification_selection_callback = self._on_notification_selected

    def stop_part(self) -> None:
        """Stops the part: pending timers must not outlive the app."""
        self._blinker.stop()
        self._cancel_all_timers()

    def _cancel_all_timers(self) -> None:
        """Cancel the queue advance and every notification's re-alert and timeout timer."""
        self._cancel_timer("_advance_handle")
        for notif_id in set(self._persistent_alert_handles) | set(self._timeout_handles):
            self._cancel_notification_timers(notif_id)

    def _cancel_notification_timers(self, notif_id: str) -> None:
        """Cancel the re-alert loop and the auto-dismiss timer of one notification."""
        for handles in (self._persistent_alert_handles, self._timeout_handles):
            handle = handles.pop(notif_id, None)
            if handle is not None:
                self.app.cancel_timer(handle)

    def _find(self, notif_id: str | None) -> Notification | None:
        """Return the queued notification with ``notif_id``, if it is still queued."""
        return next((n for n in self._notifications if n.notif_id == notif_id), None)

    # notifications

    def add_notification(
        self,
        title: str,
        message: str = "",
        icon: str = "",
        persistent: bool = False,
        force_show: bool = False,
        icon_color: int | str | list[int] | None = None,
        sound: str = DEFAULT_NOTIFICATION_SOUND,
        text_size: str | int = "auto",
        timeout: int | None = None,
    ) -> Notification:
        """Queue a notification.

        Every path (the HA service, the notify entities, the ESPHome action)
        ends up here.  A persistent notification always opens immediately.
        """
        icon_color = _normalize_icon_color(icon_color)
        sound = _normalize_sound(sound)
        force_show = force_show or persistent

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

        notification = Notification(
            title=title,
            message=message,
            icon=icon,
            persistent=persistent,
            force_show=force_show,
            icon_color=icon_color,
            sound=sound,
            text_size=text_size,
            timeout=timeout,
            notif_id=uuid.uuid4().hex,
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
            self.app.device.wake_for_notification()

        # A persistent notification must stay accessible: keep bringing its
        # popup back until the user dismisses it.
        if notification.persistent:
            self._start_persistent_alert(notification)

        # An explicit timeout auto-dismisses the notification (persistent or
        # not); without one the notification stays queued until dismissed.
        if timeout and int(timeout) > 0:
            self._start_timeout(notification)

        return notification

    def _start_timeout(self, notification: Notification) -> None:
        """Arm auto-dismissal of ``notification`` after its ``timeout``.

        On expiry the notification leaves the queue through the normal removal
        path (events, list refresh, persistent-alert cleanup included); when
        its own popup is the one on screen it is closed so the queue player
        opens the next queued notification in its place.
        """
        notif_id = notification.notif_id
        delay = int(notification.timeout or 0)

        def _expire(_data: Any = None) -> None:
            self._timeout_handles.pop(notif_id, None)
            stored = self._find(notif_id)
            if stored is not None:
                self._expire_notification(stored, notif_id)

        handle = self.app.run_in(_expire, delay)
        self._timeout_handles[notif_id] = handle

    def _expire_notification(self, notification: Notification, notif_id: str) -> None:
        """Remove an auto-dismissed notification and un-show its popup if active.

        The popup is closed only when it is *this* notification's popup (a
        queued notification must expire without disturbing another open popup
        or list).  Closing it fires the popup's close callback, which — with
        the notification already gone from the queue — arms the queue advance.
        """
        self._remove(notification)
        if not self._notification_view_open():
            return
        if self._open_popup_notif_id == notif_id:
            navigation = self.app.controller.get("navigation")
            if navigation is not None:
                self.log("Notification timed out while shown; closing its popup")
                navigation.close_panel()

    def _start_persistent_alert(self, notification: Notification) -> None:
        """Re-open a persistent notification's popup until it is dismissed.

        Arms a repeating timer that puts the notification back on screen
        every ``PERSISTENT_ALERT_INTERVAL`` seconds while it stays queued,
        the idle/screensaver page included; only a schedule entry with sound
        off keeps the display dark.  The timer stops itself once the
        notification leaves the queue (and is cancelled eagerly by
        ``_remove``/``clear_notifications``).
        """
        notif_id = notification.notif_id

        def _re_alert_tick(_data: Any = None) -> None:
            stored = self._find(notif_id)
            # Dismissed or cleared: stop the loop and drop the handle.
            if stored is None:
                handle = self._persistent_alert_handles.pop(notif_id, None)
                if handle is not None:
                    self.app.cancel_timer(handle)
                return
            # Never steal an open notification popup or list from the user.
            if self._notification_view_open():
                return
            self.open_notification(stored)
            self.app.device.wake_for_notification()

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
        # Neither a pending queue advance nor a notification's timers may
        # fire after a clear.
        self._cancel_all_timers()
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
        self._cancel_notification_timers(notification.notif_id)
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
        notif_id = notification.notif_id
        btn_right = self.translate("Dismiss")
        self.app.controller["navigation"].open_panel(
            PopupPanelKey.POPUP_NOTIFY,
            icon=notification.icon,
            title=notification.title,
            notification=notification.message,
            icon_color=notification.icon_color,
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
            PopupPanelKey.POPUP_SELECT,
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

    def _is_notification_view(self, panel: Any) -> bool:
        """True when ``panel`` is a popup/list opened by this controller.

        The ``notify`` page is also used for non-queued popups (entity
        unavailable, update notices, timer finished): the ``notif_id`` marker
        distinguishes the queued-notification popups. The system key identifies
        the panel: its type is the page's (``notify``, ``select``).
        """
        key = panel.get("key", None)
        if key == PopupPanelKey.POPUP_NOTIFY:
            return str(panel.get("notif_id", "") or "") != ""
        if key == PopupPanelKey.POPUP_SELECT:
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
        if self._find(notif_id) is not None:
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
        if panel is None or panel.get("key", None) != PopupPanelKey.POPUP_SELECT:
            return
        if not self._is_notification_view(panel):
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
            # Keep the full label in the queue model; SelectPage shortens it to
            # the selected widget's width when rendering the list.
            label = f"{title}: {message}" if message else title
            # notif_id rather than the index: the queue can change while the list is open.
            items.append({"value": n.notif_id, "name": label})
        self._list_items[:] = items

    def _on_notification_selected(self, selected_value: str | None) -> None:
        """Open the detail popup for the selected notification.

        Args:
            selected_value: ``notif_id`` of the notification. Tapping
                the selected item again passes the same value.
        """
        notification = self._find(selected_value)
        if notification is not None:
            self.open_notification(notification)

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
                "id": notification.notif_id,
                "state": state,
                "title": str(notification.title),
                "message": str(notification.message),
                "icon": notification.icon,
                "icon_color": notification.icon_color,
                "sound": notification.sound,
                "persistent": notification.persistent,
                "force_show": notification.force_show,
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
            persistent = notification.get("persistent", False)
            icon_color = notification.get("icon_color")
            sound = notification.get("sound", DEFAULT_NOTIFICATION_SOUND)
            force_show = notification.get("force_show", False)
            text_size = notification.get("text_size", "auto")
            timeout = notification.get("timeout")
            timeout = int(timeout) if timeout is not None else None
            self.add_notification(
                title=title,
                message=message,
                icon=icon,
                persistent=persistent,
                force_show=force_show,
                icon_color=icon_color,
                sound=sound,
                text_size=text_size,
                timeout=timeout,
            )
        # Also forward notification lifecycle events to the shared blinker
        # so pages don't need to handle them individually.
        self._blinker.handle_event(event)
