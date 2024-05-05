""" Unit test on :py:mod:`collectives.utils.jinja` functions. """

import datetime
from collectives.utils.jinja import helpers_processor


def test_format_date():
    """Test simple date format"""
    # Null date
    date_test = None
    date_format = helpers_processor()["format_date"](date_test)
    assert date_format == "N/A"

    # le 26 avril à 18h -> le 26 avril
    date_test = datetime.datetime(2020, 4, 26, 18, 0, 0)
    date_format = helpers_processor()["format_date"](date_test)
    assert date_format == "dimanche 26 avril 2020"


def test_format_time():
    """Test simple time format"""
    # Null date
    date_test = None
    date_format = helpers_processor()["format_time"](date_test)
    assert date_format == "N/A"

    # le 26 avril à 18h -> 18h00
    date_test = datetime.datetime(2020, 4, 26, 18, 0, 0)
    date_format = helpers_processor()["format_time"](date_test)
    assert date_format == "18h"


def test_format_datetime_range():
    """Test format of datetime range"""
    # le 26 avril
    start = datetime.datetime(2020, 4, 26, 0, 0, 0)
    end = datetime.datetime(2020, 4, 26, 0, 0, 0)
    date_format = helpers_processor()["format_datetime_range"](start, end)
    assert date_format == "dimanche 26 avril 2020"

    # le 26 avril à 18h
    start = datetime.datetime(2020, 4, 26, 18, 0, 0)
    end = datetime.datetime(2020, 4, 26, 18, 0, 0)
    date_format = helpers_processor()["format_datetime_range"](start, end)
    assert date_format == "dimanche 26 avril 2020 | 18h"

    # le 26 avril de 8h à 18h30
    start = datetime.datetime(2020, 4, 26, 8, 0, 0)
    end = datetime.datetime(2020, 4, 26, 18, 30, 0)
    date_format = helpers_processor()["format_datetime_range"](start, end)
    assert date_format == "dimanche 26 avril 2020 | 8h-18h30"

    # du 26 avril au 27 avril
    start = datetime.datetime(2020, 4, 26, 0, 0, 0)
    end = datetime.datetime(2020, 4, 27, 0, 0, 0)
    date_format = helpers_processor()["format_datetime_range"](start, end)
    assert date_format == "dimanche 26 avril 2020 au lundi 27 avril 2020"

    # du 26 avril à 8h au 27 avril à 18h30
    start = datetime.datetime(2020, 4, 26, 8, 0, 0)
    end = datetime.datetime(2020, 4, 27, 18, 30, 0)
    date_format = helpers_processor()["format_datetime_range"](start, end)
    assert date_format == "dimanche 26 avril 2020 à 8h au lundi 27 avril 2020 à 18h30"


def test_format_date_range():
    """Test how date range are printed."""
    # le 26 avril de 8h à 18h -> le 26 avril
    start = datetime.datetime(2020, 4, 26, 8, 0, 0)
    end = datetime.datetime(2020, 4, 26, 18, 0, 0)
    date_format = helpers_processor()["format_date_range"](start, end)
    assert date_format == "dim. 26 avr."

    # du 26 avril à 8h au 27 avril à 18h30 -> du 26 avril au 27 avril
    start = datetime.datetime(2020, 4, 26, 8, 0, 0)
    end = datetime.datetime(2020, 4, 27, 18, 30, 0)
    date_format = helpers_processor()["format_date_range"](start, end)
    assert date_format == "du dim. 26 avr. au lun. 27 avr."
