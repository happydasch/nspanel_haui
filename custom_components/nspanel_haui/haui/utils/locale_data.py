"""Locale data for date formatting.

Provides day/month names and format patterns for supported locales.
Replaces babel.dates.format_date with hardcoded CLDR-based data.
"""

SUPPORTED_LOCALES = frozenset({"en_US", "de_DE", "nl_NL", "pl_PL", "fr_FR"})

# Format tokens:
#   {DOW}   = full weekday name
#   {DOWA}  = abbreviated weekday name
#   {DAY}   = day of month (1-31, unpadded)
#   {MON}   = full month name
#   {MONA}  = abbreviated month name
#   {YEAR}  = full year (4-digit)

LOCALE_PATTERNS = {
    "en_US": {
        "full": "{DOW}, {MON} {DAY}, {YEAR}",
        "long": "{MON} {DAY}, {YEAR}",
        "medium": "{MONA} {DAY}, {YEAR}",
        "short": "{MONA} {DAY}, {YEAR}",  # CLDR uses M/d/yy but we keep names for consistency
        "E": "{DOWA}",
        "EEEE": "{DOW}",
    },
    "de_DE": {
        "full": "{DOW}, {DAY}. {MON} {YEAR}",
        "long": "{DAY}. {MON} {YEAR}",
        "medium": "{DAY}. {MONA} {YEAR}",
        "short": "{DAY}.{MON}.{YEAR}",  # numeric-ish format
        "E": "{DOWA}",
        "EEEE": "{DOW}",
    },
    "nl_NL": {
        "full": "{DOW} {DAY} {MON} {YEAR}",
        "long": "{DAY} {MON} {YEAR}",
        "medium": "{DAY} {MONA} {YEAR}",
        "short": "{DAY}-{MON}-{YEAR}",  # numeric-ish
        "E": "{DOWA}",
        "EEEE": "{DOW}",
    },
    "pl_PL": {
        "full": "{DOW}, {DAY} {MON} {YEAR}",
        "long": "{DAY} {MON} {YEAR}",
        "medium": "{DAY} {MONA} {YEAR}",
        "short": "{DAY}.{MON}.{YEAR}",  # numeric-ish
        "E": "{DOWA}",
        "EEEE": "{DOW}",
    },
    "fr_FR": {
        "full": "{DOW} {DAY} {MON} {YEAR}",
        "long": "{DAY} {MON} {YEAR}",
        "medium": "{DAY} {MONA} {YEAR}",
        "short": "{DAY}/{MON}/{YEAR}",  # numeric-ish
        "E": "{DOWA}",
        "EEEE": "{DOW}",
    },
}

# Day names indexed by Python weekday (0=Monday, 6=Sunday)
# Each entry: (full_names_list, abbreviated_names_list)
DAY_NAMES = {
    "en_US": (
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    ),
    "de_DE": (
        ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
        ["Mo.", "Di.", "Mi.", "Do.", "Fr.", "Sa.", "So."],
    ),
    "nl_NL": (
        ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"],
        ["ma", "di", "wo", "do", "vr", "za", "zo"],
    ),
    "pl_PL": (
        ["poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela"],
        ["pon", "wt", "sr", "czw", "pt", "sob", "nie"],
    ),
    "fr_FR": (
        ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
        ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."],
    ),
}

# Month names indexed by calendar month (0=January, 11=December)
# Each entry: (full_names_list, abbreviated_names_list)
# Polish full months use genitive case (used in date format context like "15 stycznia 2025")
MONTH_NAMES = {
    "en_US": (
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    ),
    "de_DE": (
        [
            "Januar",
            "Februar",
            "März",
            "April",
            "Mai",
            "Juni",
            "Juli",
            "August",
            "September",
            "Oktober",
            "November",
            "Dezember",
        ],
        [
            "Jan.",
            "Feb.",
            "März",
            "Apr.",
            "Mai",
            "Juni",
            "Juli",
            "Aug.",
            "Sep.",
            "Okt.",
            "Nov.",
            "Dez.",
        ],
    ),
    "nl_NL": (
        [
            "januari",
            "februari",
            "maart",
            "april",
            "mei",
            "juni",
            "juli",
            "augustus",
            "september",
            "oktober",
            "november",
            "december",
        ],
        [
            "jan.",
            "feb.",
            "mrt.",
            "apr.",
            "mei",
            "jun.",
            "jul.",
            "aug.",
            "sep.",
            "okt.",
            "nov.",
            "dec.",
        ],
    ),
    "pl_PL": (
        # Genitive case - used in full/long/medium date format contexts
        [
            "stycznia",
            "lutego",
            "marca",
            "kwietnia",
            "maja",
            "czerwca",
            "lipca",
            "sierpnia",
            "września",
            "października",
            "listopada",
            "grudnia",
        ],
        ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"],
    ),
    "fr_FR": (
        [
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ],
        [
            "janv.",
            "févr.",
            "mars",
            "avr.",
            "mai",
            "juin",
            "juil.",
            "août",
            "sept.",
            "oct.",
            "nov.",
            "déc.",
        ],
    ),
}


def get_day_name(locale: str, weekday: int, abbreviated: bool = False) -> str:
    """Return the day name for a given locale and Python weekday index.

    Args:
        locale: Locale string (e.g. "en_US", "de_DE")
        weekday: Python weekday index (0=Monday, 6=Sunday)
        abbreviated: If True, return abbreviated name

    Returns:
        Localized day name string
    """
    names = DAY_NAMES.get(locale)
    if names is None:
        names = DAY_NAMES["en_US"]
    idx = 1 if abbreviated else 0
    return names[idx][weekday]


def get_month_name(locale: str, month: int, abbreviated: bool = False) -> str:
    """Return the month name for a given locale and calendar month index.

    Args:
        locale: Locale string (e.g. "en_US", "de_DE")
        month: Calendar month index (1=January, 12=December)
        abbreviated: If True, return abbreviated name

    Returns:
        Localized month name string
    """
    names = MONTH_NAMES.get(locale)
    if names is None:
        names = MONTH_NAMES["en_US"]
    idx = 1 if abbreviated else 0
    return names[idx][month - 1]


def get_pattern(locale: str, babel_format: str) -> str | None:
    """Return the token pattern for a given locale and Babel format name.

    Args:
        locale: Locale string (e.g. "en_US", "de_DE")
        babel_format: Babel format name (e.g. "full", "E", "EEEE")

    Returns:
        Token pattern string, or None if format is not recognized
    """
    patterns = LOCALE_PATTERNS.get(locale)
    if patterns is None:
        patterns = LOCALE_PATTERNS["en_US"]
    return patterns.get(babel_format)
