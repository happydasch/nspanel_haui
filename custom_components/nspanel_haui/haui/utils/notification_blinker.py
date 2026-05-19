"""Notification indicator blinking for HAUIPage subclasses.

Manages the timer-driven blinking cycle and new-notification flag
so pages don't duplicate the timer lifecycle boilerplate.

Usage inside a page::

    # In prepare()
    self._notif_blinker = NotificationBlinker(self._refresh_notif)

    # In process_event()
    self._notif_blinker.handle_event(event)

    # In render_panel()
    self._notif_blinker.refresh()

    # In _stop_panel()
    self._notif_blinker.stop()

where ``_refresh_notif(is_blinking)`` is a page method that renders
the notification indicator (checking page config like
``_show_notifications``, calling
``self.update_function_component(...)``, etc.).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


class NotificationBlinker:
    """Manages a notification indicator's blinking state and timer.

    Parameters
    ----------
    refresh_fn
        A no-argument callable that re-renders the notification
        indicator.  Called on each blink tick and on ``refresh()``.
        The page should check :attr:`new_notifications` inside this
        callback to decide whether to show blinking or static state.
    interval
        Blink interval in seconds (default 1.0).
    """

    def __init__(
        self,
        refresh_fn: Callable[[], None],
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
