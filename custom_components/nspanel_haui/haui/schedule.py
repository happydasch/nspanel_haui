"""Device schedule: time windows that override sound, brightness and display-off.

An entry is active from its start to its end; each boundary is a local clock
time (``HH:MM``) or a sun event (``sunrise`` / ``sunset``) shifted by an offset
in minutes.  Outside every window the device's normal settings apply, and so
does every value an entry leaves unset (``None``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from datetime import time as dt_time
from typing import Any

SUN_EVENTS: tuple[str, ...] = ("sunrise", "sunset")

# Local time of a sun event on a date, or None where the sun does not rise or
# set that day.
SunTime = Callable[[str, date], datetime | None]


@dataclass(frozen=True)
class ScheduleEntry:
    """One schedule window and the settings it applies.

    A ``None`` value means the entry does not set it: the device setting of the
    same name applies.
    """

    start: str
    end: str
    sound: bool
    brightness: int | None
    display_off: bool
    timeout_display_off: int | None
    # Minutes added to a sun event boundary; unused for a clock time.
    start_offset: int = 0
    end_offset: int = 0
    brightness_dim: int | None = None
    timeout_dimming: int | None = None
    duration_dimming: float | None = None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> ScheduleEntry:
        """Build an entry from one item of the ``schedule`` device setting."""
        return cls(
            start=config["start"],
            end=config["end"],
            sound=config["sound"],
            brightness=config.get("brightness"),
            display_off=config["display_off"],
            timeout_display_off=config.get("timeout_display_off"),
            start_offset=config.get("start_offset", 0),
            end_offset=config.get("end_offset", 0),
            brightness_dim=config.get("brightness_dim"),
            timeout_dimming=config.get("timeout_dimming"),
            duration_dimming=config.get("duration_dimming"),
        )


def parse_boundary(value: str) -> dt_time | None:
    """Return the clock time of ``HH:MM``, or None for a sun event.

    Raises:
        ValueError: ``value`` is neither a sun event nor a ``HH:MM`` time.
    """
    if value in SUN_EVENTS:
        return None
    return datetime.strptime(value, "%H:%M").time()


def _boundary(
    value: str, offset: int, day: date, now: datetime, sun_time: SunTime
) -> datetime | None:
    """The moment of a boundary on ``day``; None when the sun event is missing.

    A sun event's offset can move it past midnight, into the neighbouring day.
    """
    clock = parse_boundary(value)
    if clock is not None:
        return datetime.combine(day, clock, tzinfo=now.tzinfo)
    point = sun_time(value, day)
    return point + timedelta(minutes=offset) if point is not None else None


def active_entry(
    entries: list[ScheduleEntry], now: datetime, sun_time: SunTime
) -> ScheduleEntry | None:
    """Return the first entry whose window contains ``now``.

    The end is exclusive and a window may span midnight.  Sun events use
    today's times for both boundaries.
    """
    now_time = now.time()
    for entry in entries:
        start = _boundary(entry.start, entry.start_offset, now.date(), now, sun_time)
        end = _boundary(entry.end, entry.end_offset, now.date(), now, sun_time)
        if start is None or end is None:
            continue
        start_time, end_time = start.time(), end.time()
        if start_time < end_time:
            if start_time <= now_time < end_time:
                return entry
        elif start_time > end_time and (now_time >= start_time or now_time < end_time):
            return entry
    return None


def next_boundary(
    entries: list[ScheduleEntry], now: datetime, sun_time: SunTime
) -> datetime | None:
    """Return the next moment any entry starts or ends, up to the end of tomorrow.

    Yesterday's sun events count too: an offset can move one into today.
    """
    future: list[datetime] = []
    for day_offset in (-1, 0, 1):
        day = now.date() + timedelta(days=day_offset)
        for entry in entries:
            for value, offset in (
                (entry.start, entry.start_offset),
                (entry.end, entry.end_offset),
            ):
                point = _boundary(value, offset, day, now, sun_time)
                if point is not None and point > now:
                    future.append(point)
    return min(future) if future else None
