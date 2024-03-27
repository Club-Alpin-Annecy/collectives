"""Unit tests for CSV import"""

from io import StringIO
import datetime

from collectives.utils.csv import csv_to_events


def test_csv_import(user1):
    """Test importing an event CSV file"""

    # pylint: disable=C0301
    csv = f""",,,,,,,,,,,,,,,,\naccess libre,Mr TEST,{user1.license},26/11/2021 7:00,26/11/2021 7:00,Aiguille des Calvaires,Aravis,d,2322,1200,F,120,d ,8,4,19/11/2021 7:00,25/11/2021 12:00,,rando cool"""

    output = StringIO(csv)
    events, processed, failed = csv_to_events(
        output, "{altitude}m-{denivele}m-{cotation}"
    )
    assert len(events) == 1
    event = events[0]
    assert processed == 1
    assert not failed
    assert event.title == "Aiguille des Calvaires"
    assert event.num_slots == 8
    assert event.num_online_slots == 4
    assert event.registration_open_time == datetime.datetime(2021, 11, 19, 7, 0, 0)
    assert event.registration_close_time == datetime.datetime(2021, 11, 25, 12, 0, 0)
    assert "2322m-1200m-F" in event.rendered_description
    assert event.leaders[0].license == user1.license
    assert len(event.tags) == 1
    assert event.tag_refs[0].name == "Rando Cool"
