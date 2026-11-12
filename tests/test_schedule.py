"""Tests for the device schedule's window logic (``haui/schedule.py``)."""

from datetime import datetime
from datetime import time as dt_time

import pytest

from custom_components.nspanel_haui.haui.schedule import (
    ScheduleEntry,
    active_entry,
    next_boundary,
    parse_boundary,
)

SUN = {"sunrise": dt_time(7, 12, 30), "sunset": dt_time(17, 5)}


def _sun_time(event, day):
    return datetime.combine(day, SUN[event])


def _no_sun(event, day):
    return None


def _entry(start, end, brightness=20, start_offset=0, end_offset=0):
    return ScheduleEntry(
        start=start,
        end=end,
        sound=True,
        brightness=brightness,
        display_off=True,
        timeout_display_off=30,
        start_offset=start_offset,
        end_offset=end_offset,
    )


def test_entry_is_built_from_its_stored_config():
    entry = ScheduleEntry.from_config(
        {
            "start": "22:00",
            "end": "sunrise",
            "sound": False,
            "brightness": 5,
            "display_off": False,
            "timeout_display_off": 60,
        }
    )

    assert entry == ScheduleEntry("22:00", "sunrise", False, 5, False, 60)
    assert (entry.start_offset, entry.end_offset) == (0, 0)
    # Values the entry leaves out are inherited from the device settings.
    assert (entry.brightness_dim, entry.timeout_dimming, entry.duration_dimming) == (
        None,
        None,
        None,
    )


def test_entry_reads_the_dimming_settings_it_sets():
    entry = ScheduleEntry.from_config(
        {
            "start": "22:00",
            "end": "07:00",
            "sound": True,
            "brightness": 5,
            "brightness_dim": 2,
            "display_off": True,
            "timeout_dimming": 5,
            "timeout_display_off": 60,
            "duration_dimming": 1.5,
        }
    )

    assert (entry.brightness, entry.brightness_dim) == (5, 2)
    assert (entry.timeout_dimming, entry.timeout_display_off) == (5, 60)
    assert entry.duration_dimming == 1.5


def test_entry_reads_its_sun_offsets():
    entry = ScheduleEntry.from_config(
        {
            "start": "sunset",
            "start_offset": -30,
            "end": "sunrise",
            "end_offset": 45,
            "sound": True,
            "brightness": 5,
            "display_off": True,
            "timeout_display_off": 60,
        }
    )

    assert (entry.start_offset, entry.end_offset) == (-30, 45)


def test_parse_boundary_reads_clock_times_and_leaves_sun_events():
    assert parse_boundary("06:30") == dt_time(6, 30)
    assert parse_boundary("sunrise") is None
    assert parse_boundary("sunset") is None


@pytest.mark.parametrize("value", ["", "25:00", "noon", "7"])
def test_parse_boundary_rejects_other_values(value):
    with pytest.raises(ValueError):
        parse_boundary(value)


@pytest.mark.parametrize(
    ("now", "active"),
    [
        (datetime(2026, 1, 1, 9, 59), False),
        (datetime(2026, 1, 1, 10, 0), True),
        (datetime(2026, 1, 1, 13, 59), True),
        # The end is exclusive: the entry is over at 14:00.
        (datetime(2026, 1, 1, 14, 0), False),
    ],
)
def test_same_day_window(now, active):
    entry = _entry("10:00", "14:00")

    assert (active_entry([entry], now, _sun_time) is entry) is active


@pytest.mark.parametrize(
    ("now", "active"),
    [
        (datetime(2026, 1, 1, 21, 59), False),
        (datetime(2026, 1, 1, 22, 0), True),
        (datetime(2026, 1, 2, 2, 0), True),
        (datetime(2026, 1, 2, 6, 0), False),
        (datetime(2026, 1, 2, 12, 0), False),
    ],
)
def test_overnight_window(now, active):
    entry = _entry("22:00", "06:00")

    assert (active_entry([entry], now, _sun_time) is entry) is active


@pytest.mark.parametrize(
    ("now", "active"),
    [
        (datetime(2026, 1, 1, 17, 4), False),
        (datetime(2026, 1, 1, 17, 5), True),
        (datetime(2026, 1, 2, 7, 12), True),
        (datetime(2026, 1, 2, 7, 13), False),
    ],
)
def test_window_between_sun_events(now, active):
    entry = _entry("sunset", "sunrise")

    assert (active_entry([entry], now, _sun_time) is entry) is active


@pytest.mark.parametrize(
    ("now", "active"),
    [
        # Sunset 17:05 minus 30 minutes, sunrise 07:12:30 plus 45 minutes.
        (datetime(2026, 1, 1, 16, 34), False),
        (datetime(2026, 1, 1, 16, 35), True),
        (datetime(2026, 1, 2, 7, 57), True),
        (datetime(2026, 1, 2, 7, 58), False),
    ],
)
def test_sun_events_are_shifted_by_their_offsets(now, active):
    entry = _entry("sunset", "sunrise", start_offset=-30, end_offset=45)

    assert (active_entry([entry], now, _sun_time) is entry) is active


def test_one_sun_event_with_two_offsets_is_a_window():
    entry = _entry("sunrise", "sunrise", start_offset=-60, end_offset=60)

    assert active_entry([entry], datetime(2026, 1, 1, 7, 0), _sun_time) is entry
    assert active_entry([entry], datetime(2026, 1, 1, 9, 0), _sun_time) is None


def test_an_offset_does_not_shift_a_clock_time():
    entry = _entry("10:00", "14:00", start_offset=120, end_offset=120)

    assert active_entry([entry], datetime(2026, 1, 1, 10, 30), _sun_time) is entry
    assert next_boundary([entry], datetime(2026, 1, 1, 10, 30), _sun_time) == datetime(
        2026, 1, 1, 14, 0
    )


def test_next_boundary_includes_the_sun_offset():
    entries = [_entry("sunset", "sunrise", start_offset=-30, end_offset=45)]

    assert next_boundary(entries, datetime(2026, 1, 1, 12, 0), _sun_time) == datetime(
        2026, 1, 1, 16, 35
    )
    assert next_boundary(entries, datetime(2026, 1, 1, 18, 0), _sun_time) == datetime(
        2026, 1, 2, 7, 57, 30
    )


def test_an_offset_past_midnight_is_a_boundary_of_the_next_day():
    # Sunset 17:05 plus 8 hours is 01:05 on the following day.
    entries = [_entry("12:00", "sunset", end_offset=480)]

    assert active_entry(entries, datetime(2026, 1, 2, 0, 30), _sun_time) is entries[0]
    assert next_boundary(entries, datetime(2026, 1, 1, 23, 0), _sun_time) == datetime(
        2026, 1, 2, 1, 5
    )
    # Still found after midnight, when it belongs to yesterday's sunset.
    assert next_boundary(entries, datetime(2026, 1, 2, 0, 30), _sun_time) == datetime(
        2026, 1, 2, 1, 5
    )


def test_a_clock_time_and_a_sun_event_can_be_mixed():
    entry = _entry("21:00", "sunrise")

    assert active_entry([entry], datetime(2026, 1, 2, 7, 0), _sun_time) is entry
    assert active_entry([entry], datetime(2026, 1, 2, 8, 0), _sun_time) is None


def test_the_first_matching_entry_wins():
    first, second = _entry("22:00", "06:00", 5), _entry("20:00", "23:30", 40)

    assert active_entry([first, second], datetime(2026, 1, 1, 23, 0), _sun_time) is first
    assert active_entry([first, second], datetime(2026, 1, 1, 21, 0), _sun_time) is second


def test_no_entry_is_active_outside_every_window():
    entries = [_entry("22:00", "06:00"), _entry("12:00", "13:00")]

    assert active_entry(entries, datetime(2026, 1, 1, 15, 0), _sun_time) is None


def test_an_entry_without_its_sun_event_is_never_active():
    entry = _entry("sunset", "06:00")

    assert active_entry([entry], datetime(2026, 1, 1, 23, 0), _no_sun) is None


def test_next_boundary_is_the_nearest_start_or_end():
    entries = [_entry("10:00", "14:00"), _entry("22:00", "06:00")]

    assert next_boundary(entries, datetime(2026, 1, 1, 9, 0), _sun_time) == datetime(
        2026, 1, 1, 10, 0
    )
    assert next_boundary(entries, datetime(2026, 1, 1, 12, 0), _sun_time) == datetime(
        2026, 1, 1, 14, 0
    )
    # After the last boundary of the day: the first one tomorrow.
    assert next_boundary(entries, datetime(2026, 1, 1, 23, 0), _sun_time) == datetime(
        2026, 1, 2, 6, 0
    )


def test_next_boundary_is_after_now_even_on_a_boundary():
    entries = [_entry("10:00", "14:00")]

    assert next_boundary(entries, datetime(2026, 1, 1, 10, 0), _sun_time) == datetime(
        2026, 1, 1, 14, 0
    )


def test_next_boundary_uses_the_sun_times_of_each_day():
    entries = [_entry("sunset", "sunrise")]

    assert next_boundary(entries, datetime(2026, 1, 1, 12, 0), _sun_time) == datetime(
        2026, 1, 1, 17, 5
    )
    assert next_boundary(entries, datetime(2026, 1, 1, 18, 0), _sun_time) == datetime(
        2026, 1, 2, 7, 12, 30
    )


def test_next_boundary_is_none_without_entries_or_sun_events():
    assert next_boundary([], datetime(2026, 1, 1, 12, 0), _sun_time) is None
    assert next_boundary([_entry("sunset", "sunrise")], datetime(2026, 1, 1), _no_sun) is None
