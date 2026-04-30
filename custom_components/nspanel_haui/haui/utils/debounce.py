"""Simple debouncer for suppressing noisy state-change events (state flapping) that would otherwise cause repeated UI updates.

Uses :class:`threading.Timer` internally, which is safe in the executor thread context.
"""

from __future__ import annotations

import threading
from collections.abc import Callable


class Debouncer:
    """Simple debouncer.

    Parameters
    ----------
    delay
        Minimum delay (seconds) before the callback is executed.
    """

    def __init__(self, delay: float = 0.3):
        self.delay = delay
        self._timers: dict[str, threading.Timer] = {}

    def call(self, key: str, func: Callable[[], None]) -> None:
        """Schedule *func* to be called after :attr:`delay` seconds.

        If a previous timer for *key* exists, it is cancelled.
        """
        # Cancel previous timer if it exists
        if key in self._timers:
            self._timers[key].cancel()

        # Create a new timer
        timer = threading.Timer(self.delay, func)
        self._timers[key] = timer
        timer.start()

    def cancel(self, key: str) -> None:
        """Cancel the timer associated with *key* if it exists."""
        timer = self._timers.pop(key, None)
        if timer:
            timer.cancel()

    def clear_all(self) -> None:
        """Cancel all scheduled timers."""
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()
