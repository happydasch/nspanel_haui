"""Debouncer for suppressing noisy state-change events (state flapping).

Uses :class:`threading.Timer` internally. When *executor* is provided,
timer callbacks are dispatched to the HA executor thread so page code
always runs on the correct thread.
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
    executor
        Optional callable that takes a no-arg function and schedules it
        on the HA executor thread. If ``None`` the callback runs on the
        timer thread directly (legacy behaviour).
    """

    def __init__(
        self,
        delay: float = 0.3,
        executor: Callable[[Callable[[], None]], None] | None = None,
    ):
        self.delay = delay
        self._timers: dict[str, threading.Timer] = {}
        self._executor = executor

    def call(self, key: str, func: Callable[[], None]) -> None:
        """Schedule *func* to be called after :attr:`delay` seconds.

        If a previous timer for *key* exists, it is cancelled.
        """
        # Cancel previous timer if it exists
        if key in self._timers:
            self._timers[key].cancel()

        # Wrap in executor dispatch when available
        executor = self._executor
        if executor is not None:

            def _wrapped(f: Callable[[], None] = func) -> None:
                executor(f)

            timer_func: Callable[[], None] = _wrapped
        else:
            timer_func = func

        # Create a new timer
        timer = threading.Timer(self.delay, timer_func)
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
