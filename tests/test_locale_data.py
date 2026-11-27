"""Locale date layouts, and the names they were stored under before the rename."""

from __future__ import annotations

from datetime import datetime

import pytest

from custom_components.nspanel_haui.haui.utils.datetime import format_datetime
from custom_components.nspanel_haui.haui.utils.locale_data import get_pattern

THURSDAY = datetime(2026, 11, 12)


def test_the_weekday_layouts_show_the_weekday_only():
    """The two non-CLDR layouts Home Assistant can name as a translation key."""
    assert format_datetime(THURSDAY, "%x", "weekday_short", "en_US") == "Thu"
    assert format_datetime(THURSDAY, "%x", "weekday_full", "en_US") == "Thursday"


@pytest.mark.parametrize(
    ("stored", "current", "expected"),
    [("E", "weekday_short", "Do."), ("EEEE", "weekday_full", "Donnerstag")],
)
def test_a_layout_stored_under_its_old_name_keeps_its_pattern(stored, current, expected):
    """A panel saved as ``E``/``EEEE`` shows its weekday, not the strftime fallback."""
    assert get_pattern("de_DE", stored) == get_pattern("de_DE", current)
    assert format_datetime(THURSDAY, "%x", stored, "de_DE") == expected
