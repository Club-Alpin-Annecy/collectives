"""Functions to help on standard taks
"""
from datetime import datetime

from dateutil import tz

from flask import current_app


def current_time():
    tz_name = current_app.config["TZ_NAME"]
    tz_info = tz.gettz(tz_name)
    now = datetime.now(tz_info)
    # Datetimes are stored in naive format, assumed to
    # always be in the correct timezone
    # For Python to allow comparisons we need to strip the
    # tz information from our local time
    return now.replace(tzinfo=None)
