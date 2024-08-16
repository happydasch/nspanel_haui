import datetime

# check Babel
import importlib

babel_spec = importlib.util.find_spec("babel")
if babel_spec is not None:
    import babel.dates


def get_time_localized(timeformat):
    """ Returns a localized time string of current time.

    Returns:
        str: Localized time string
    """
    time = datetime.datetime.now().strftime(timeformat)
    return time


def get_date_localized(strftime_format, babel_format, locale):
    """ Returns a localized date string of current date.

    Args:
        strftime_format (str): strftime format
        babel_format (str): babel format
        locale (str): locale

    Returns:
        str: Localized date string
    """
    dt = datetime.datetime.now()
    return format_datetime(dt, strftime_format, babel_format, locale)


def format_datetime(dt, strftime_format, babel_format, locale):
    """ Returns a localized date string.

    Args:
        strftime_format (str): strftime format
        babel_format (str): babel format
        locale (str): locale

    Returns:
        str: Localized date string
    """
    global babel_spec
    if babel_spec is not None and babel_format is not None:
        return babel.dates.format_date(dt, babel_format, locale=locale)
    else:
        return dt.strftime(strftime_format)
