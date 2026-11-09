"""Notification indicator blinking for HAUIPage subclasses.

Sits on the NotificationController so pages share a single blinker
instead of each creating their own 1-second timer.

Usage inside a page::

    # In start_panel()
    self.app.controller["notification"].set_blinker_callback(
        self._refresh_notif
    )

    # In render_panel()
    self.app.controller["notification"].blinker.refresh()

    # In _stop_panel()
    self.app.controller["notification"].clear_blinker_callback()

where ``_refresh_notif`` is a page method that renders the
notification indicator (checking page config like
``_show_notifications``, calling
``self.update_function_component(...)``, etc.).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from ..mapping.const import NotifEvent


def _noop() -> None:
    """No-op sentinel for when no page has registered a callback."""


def _always() -> bool:
    return True


class BlinkScheduler(Protocol):
    """The app timers the blinker runs on (``HAAdapter.run_every``/``cancel_timer``).

    Their callbacks run on the app's worker thread, like all other page code.
    """

    def run_every(self, cb: Callable[[Any], None], start: Any, interval: float) -> str: ...

    def cancel_timer(self, handle: str) -> None: ...


class NotificationBlinker:
    """Manages a notification indicator's blinking state and timer.

    Parameters
    ----------
    scheduler
        App timers that run the blink ticks on the app's worker thread.
    refresh_fn
        A no-argument callable that re-renders the notification
        indicator.  Called on each blink tick and on ``refresh()``.
        The page should check :attr:`new_notifications` inside this
        callback to decide whether to show blinking or static state.
        Defaults to a no-op.
    visible_fn
        Whether the display is visible.  Blink ticks are skipped while it is
        dark, so an unread notification does not send a display command every
        second all night.  Defaults to always visible.
    interval
        Blink interval in seconds (default 1.0).
    """

    def __init__(
        self,
        scheduler: BlinkScheduler,
        refresh_fn: Callable[[], None] = _noop,
        visible_fn: Callable[[], bool] = _always,
        interval: float = 1.0,
    ) -> None:
        self._scheduler = scheduler
        self._refresh_fn = refresh_fn
        self._visible_fn = visible_fn
        self._interval = interval
        self._handle: str | None = None
        self._new_notifications = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def new_notifications(self) -> bool:
        """Whether new (unread) notifications are present."""
        return self._new_notifications

    def set_callback(self, refresh_fn: Callable[[], None]) -> None:
        """Set the refresh callback and start the blink cycle if needed.

        Called when a page activates (start_panel) to register its
        notification indicator renderer.
        """
        self._refresh_fn = refresh_fn
        if self._new_notifications:
            self._update()

    def clear_callback(self) -> None:
        """Clear the refresh callback and stop the blink timer.

        Called when a page deactivates (_stop_panel).
        """
        self._refresh_fn = _noop
        self.stop()

    def stop(self) -> None:
        """Cancel the blinking timer, if active."""
        if self._handle is not None:
            self._scheduler.cancel_timer(self._handle)
            self._handle = None

    def mark_read(self) -> None:
        """Clear the new-notifications flag and stop blinking.

        Called when the user views the notifications or none are left.
        """
        self._new_notifications = False
        self.stop()

    def refresh(self) -> None:
        """Re-render the indicator once, without scheduling a timer.

        Use this from ``render_panel()`` for static display.
        """
        self._refresh_fn()

    def handle_event(self, event: Any) -> None:
        """Process a notification event and update the indicator.

        Recognised event names:

        * ``NotifEvent.NOTIF_ADD`` — sets the new-notifications flag and
          starts blinking.
        * ``NotifEvent.NOTIF_REMOVE`` — refreshes the indicator without
          changing the flag.
        * ``NotifEvent.NOTIF_CLEAR`` — clears the flag, stops blinking,
          shows static indicator.
        """
        name = getattr(event, "name", event)
        if name not in _NOTIFICATION_EVENTS:
            return

        if name == NotifEvent.NOTIF_ADD:
            self._new_notifications = True
        elif name == NotifEvent.NOTIF_CLEAR:
            self._new_notifications = False

        self._update()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _update(self) -> None:
        """Render the indicator now and run the blink timer while unread."""
        self._refresh_fn()
        if not self._new_notifications:
            self.stop()
        elif self._handle is None:
            self._handle = self._scheduler.run_every(self._blink, None, self._interval)

    def _blink(self, _kwargs: Any = None) -> None:
        """One blink tick; the page alternates the indicator by the clock."""
        if self._visible_fn():
            self._refresh_fn()


_NOTIFICATION_EVENTS: frozenset[str] = frozenset(
    {
        NotifEvent.NOTIF_ADD,
        NotifEvent.NOTIF_REMOVE,
        NotifEvent.NOTIF_CLEAR,
    }
)
