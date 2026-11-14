from __future__ import annotations

import datetime
import zoneinfo

from .locale_data import (
    get_day_name,
    get_month_name,
    get_pattern,
)


def _get_now(timezone: str | None = None) -> datetime.datetime:
    """Return the current datetime, optionally in the given timezone.

    Args:
        timezone: IANA timezone string (e.g. "America/New_York") or None
                  to use the host machine's local time.

    Returns:
        datetime.datetime: Current datetime in the requested timezone.
    """
    if timezone:
        return datetime.datetime.now(tz=zoneinfo.ZoneInfo(timezone))
    return datetime.datetime.now()


def get_time_localized(timeformat: str, timezone: str | None = None) -> str:
    """Returns a localized time string of current time.

    Args:
        timeformat: strftime format string.
        timezone: Optional IANA timezone string. Uses HA timezone if provided,
                  otherwise host local time.

    Returns:
        str: Localized time string
    """
    time = _get_now(timezone).strftime(timeformat)
    return time


def get_date_localized(
    strftime_format: str, babel_format: str, locale: str, timezone: str | None = None
) -> str:
    """Returns a localized date string of current date.

    Args:
        strftime_format (str): strftime format
        babel_format (str): babel format
        locale (str): locale
        timezone: Optional IANA timezone string.

    Returns:
        str: Localized date string
    """
    dt = _get_now(timezone)
    return format_datetime(dt, strftime_format, babel_format, locale)


def format_datetime(dt: datetime.date, strftime_format: str, babel_format: str, locale: str) -> str:
    """Returns a localized date string.

    Args:
        strftime_format (str): strftime format
        babel_format (str): babel format
        locale (str): locale

    Returns:
        str: Localized date string
    """
    if babel_format is not None:
        pattern = get_pattern(locale, babel_format)
        if pattern is not None:
            dow = dt.weekday()  # 0=Monday
            day = dt.day
            month = dt.month  # 1=January
            year = dt.year

            result = pattern
            result = result.replace("{DOW}", get_day_name(locale, dow, abbreviated=False))
            result = result.replace("{DOWA}", get_day_name(locale, dow, abbreviated=True))
            result = result.replace("{DAY}", str(day))
            result = result.replace("{MON}", get_month_name(locale, month, abbreviated=False))
            result = result.replace("{MONA}", get_month_name(locale, month, abbreviated=True))
            result = result.replace("{YEAR}", str(year))
            return result

    # Fallback to strftime
    return dt.strftime(strftime_format)


def _parse_iso(state: str) -> datetime.date | datetime.time | None:
    """A date, a time or a date and time in ISO 8601, as Home Assistant states hold them."""
    try:
        return datetime.date.fromisoformat(state)
    except ValueError:
        pass
    try:
        return datetime.time.fromisoformat(state)
    except ValueError:
        pass
    try:
        return datetime.datetime.fromisoformat(state)
    except ValueError:
        return None


def format_state_datetime(
    state: str,
    time_format: str,
    date_format: str,
    babel_format: str,
    locale: str,
    timezone: str,
) -> str | None:
    """An entity state holding a date, a time or both, in the device's formats.

    A date and time is shown as the date followed by the time; one with a UTC
    offset (a timestamp) is first moved to Home Assistant's time zone.

    Args:
        state (str): entity state, e.g. "2026-11-14T09:30:00+00:00"
        time_format (str): strftime time format
        date_format (str): strftime date format, used when *babel_format* names no layout
        babel_format (str): locale date layout ("full", "short", …) or ""
        locale (str): locale
        timezone (str): IANA time zone of Home Assistant

    Returns:
        str | None: The formatted state, None when it is no date or time
            (``unknown``, ``unavailable``).
    """
    value = _parse_iso(state)
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is not None:
            value = value.astimezone(zoneinfo.ZoneInfo(timezone))
        date = format_datetime(value, date_format, babel_format, locale)
        return f"{date} {value.strftime(time_format)}"
    if isinstance(value, datetime.date):
        return format_datetime(value, date_format, babel_format, locale)
    return value.strftime(time_format)
