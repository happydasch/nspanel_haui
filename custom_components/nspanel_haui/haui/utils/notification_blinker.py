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

import threading
from collections.abc import Callable
from typing import Any


def _noop() -> None:
    """No-op sentinel for when no page has registered a callback."""


class NotificationBlinker:
    """Manages a notification indicator's blinking state and timer.

    Parameters
    ----------
    refresh_fn
        A no-argument callable that re-renders the notification
        indicator.  Called on each blink tick and on ``refresh()``.
        The page should check :attr:`new_notifications` inside this
        callback to decide whether to show blinking or static state.
        Defaults to a no-op.
    interval
        Blink interval in seconds (default 1.0).
    """

    def __init__(
        self,
        refresh_fn: Callable[[], None] = _noop,
        interval: float = 1.0,
    ) -> None:
        self._refresh_fn = refresh_fn
        self._interval = interval
        self._timer: threading.Timer | None = None
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
            self._tick()

    def clear_callback(self) -> None:
        """Clear the refresh callback and stop the blink timer.

        Called when a page deactivates (_stop_panel).
        """
        self._refresh_fn = _noop
        self.stop()

    def stop(self) -> None:
        """Cancel the blinking timer, if active."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def refresh(self) -> None:
        """Re-render the indicator once, without scheduling a timer.

        Use this from ``render_panel()`` for static display.
        """
        self._refresh_fn()

    def handle_event(self, event: Any) -> None:
        """Process a notification event and update the indicator.

        Recognised event names:

        * ``"SEND_NOTIFICATION"``, ``"NOTIF_ADD"`` — sets the
          new-notifications flag and starts blinking.
        * ``"NOTIF_REMOVE"`` — refreshes the indicator without changing
          the flag.
        * ``"NOTIF_CLEAR"`` — clears the flag, stops blinking, shows
          static indicator.
        """
        name = getattr(event, "name", event)
        if name not in _NOTIFICATION_EVENTS:
            return

        if name == "NOTIF_ADD":
            self._new_notifications = True
        elif name == "NOTIF_CLEAR":
            self._new_notifications = False
            self.stop()

        self._tick()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        """Call the refresh function and schedule the next blink."""
        self._refresh_fn()

        if self._new_notifications:
            self._timer = threading.Timer(self._interval, self._tick)
            self._timer.daemon = True
            self._timer.start()


_NOTIFICATION_EVENTS: frozenset[str] = frozenset(
    {
        "SEND_NOTIFICATION",
        "NOTIF_ADD",
        "NOTIF_REMOVE",
        "NOTIF_CLEAR",
    }
)
