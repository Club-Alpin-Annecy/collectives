"""Helpers functions that are make available to Jinja
"""
from datetime import time
from .helpers import current_time

# Server may not have fr_FR locale installed, for convenience
# simply define days of weeks and months names here
fr_week_days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
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


def helpers_processor():
    def format_date(datetime):
        if datetime is None:
            return "N/A"
        return "{} {} {} {}".format(
            fr_week_days[datetime.weekday()],
            datetime.day,
            fr_months[datetime.month - 1],
            datetime.year,
        )

    def format_date_short(datetime):
        if datetime is None:
            return "N/A"
        return "{}. {} {}".format(
            fr_week_days[datetime.weekday()][0:3],
            datetime.day,
            fr_short_months[datetime.month - 1],
        )

    def format_time(datetime):
        if datetime is None:
            return "N/A"
        return u"{h}h{m:02d}".format(h=datetime.hour, m=datetime.minute)

    def format_datetime_range(start, end):
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
        if start.date() == end.date():
            return "{}".format(format_date_short(start))
        return "du {} au {}".format(format_date_short(start), format_date_short(end))

    def server_local_time():
        return current_time()

    return dict(
        format_date=format_date,
        format_time=format_time,
        format_date_range=format_date_range,
        format_datetime_range=format_datetime_range,
        server_local_time=server_local_time,
    )
