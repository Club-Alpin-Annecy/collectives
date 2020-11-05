""" Module for time management and display.
"""
from datetime import datetime, time
from dateutil import tz
from flask import current_app

fr_week_days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
""" Day of week in French.

Server may not have fr_FR locale installed, for convenience, we
simply define days of weeks names here"""
fr_months = [
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
]
""" Months in French.

Server may not have fr_FR locale installed, for convenience, we
simply define months names here"""
fr_short_months = [
    "jan.",
    "fév.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sep.",
    "oct.",
    "nov.",
    "déc.",
]
""" Months abbreviations in French.

Server may not have fr_FR locale installed, for convenience, we
simply define months abbreviations here"""


def current_time():
    """Return current time in the defined time zone.

    See :py:data:`config.TZ_NAME`

    Datetimes are stored in naive format, assumed to
    always be in the correct timezone.
    For Python to be able to compare, dates must be stripped from the
    tz information from our local time

    :return: Current time
    :rtype: :py:class:`datetime.datetime`
    """
    tz_name = current_app.config["TZ_NAME"]
    tz_info = tz.gettz(tz_name)
    now = datetime.now(tz_info)

    return now.replace(tzinfo=None)


def format_date(value):
    """Format a date. (eg "Samedi 16 février 2020").

    :param value: Date to format
    :type value: :py:class:`datetime.datetime`
    :return: Formatted date
    :rtype: string"""
    if value is None:
        return "N/A"
    return "{} {} {} {}".format(
        fr_week_days[value.weekday()],
        value.day,
        fr_months[value.month - 1],
        value.year,
    )


def format_date_short(value):
    """Format a date. (eg "Sam 16 février").

    :param value: Date to format
    :type value: :py:class:`datetime.datetime`
    :return: Formatted date
    :rtype: string"""
    if value is None:
        return "N/A"
    return "{}. {} {}".format(
        fr_week_days[value.weekday()][0:3], value.day, fr_short_months[value.month - 1],
    )


def format_time(value):
    """Format a time. (eg "8h12").

    :param value: Date to format
    :type value: :py:class:`datetime.datetime`
    :return: Formatted date
    :rtype: string"""
    if value is None:
        return "N/A"
    return "{h}h{m:02d}".format(h=value.hour, m=value.minute)


def format_datetime(value):
    """Format a date + time. (eg "Samedi 16 février 2020 à 8h00").

    :param value: Date to format
    :type value: :py:class:`datetime.datetime`
    :return: Formatted date
    :rtype: string"""
    return f"{format_date(value)} à {format_time(value)}"


def format_datetime_range(start, end):
    """Format a range of dates. (eg "Samedi 12 février 2018 à 08:00 au Dimanche
    13 février 2018 à 15:00").

    - If ``start`` and ``end`` are the same day, day is not repeated.
    - If ``start`` and ``end`` are the same, it is not treated as a range.
    - If ``start`` and ``end`` are at 0h00, time is not formatted.

    :param start: Range start date.
    :type start: :py:class:`datetime.datetime`
    :param end: Range end date.
    :type end: :py:class:`datetime.datetime`
    :return: Formatted date range.
    :rtype: string"""
    if start == end:
        if start.time() == time(0):
            return "{}".format(format_date(start))
        return "{} à {}".format(format_date(start), format_time(start))
    if start.date() == end.date():
        return "{} de {} à {}".format(
            format_date(start), format_time(start), format_time(end)
        )
    if start.time() == time(0) and end.time() == time(0):
        return "du {} au {}".format(format_date(start), format_date(end))
    return "du {} à {} au {} à {}".format(
        format_date(start), format_time(start), format_date(end), format_time(end),
    )


def format_date_range(start, end):
    """Format a range of dates without their time. (eg "Samedi 12 février 2018 au
    Dimanche 13 février 2018").

    :param start: Range start date.
    :type start: :py:class:`datetime.datetime`
    :param end: Range end date.
    :type end: :py:class:`datetime.datetime`
    :return: Formatted date range.
    :rtype: string"""
    if start.date() == end.date():
        return "{}".format(format_date_short(start))
    return "du {} au {}".format(format_date_short(start), format_date_short(end))


def server_local_time():
    """ Alias of :py:func:`current_time`"""
    return current_time()
