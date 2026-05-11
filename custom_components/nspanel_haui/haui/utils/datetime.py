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


def format_datetime(
    dt: datetime.datetime, strftime_format: str, babel_format: str, locale: str
) -> str:
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
