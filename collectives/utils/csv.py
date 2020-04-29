""" Module to handle csv import
"""
from datetime import datetime
import codecs
import csv

from flask import current_app

from ..models import User, Event, db


def fill_from_csv(event, row, template):
    """ Fill an Event object attributes with parameter from a csv row.

    :param event: The evet object to populate.
    :type event: :py:class:`collectives.models.event.Event`
    :param row: List of value from a csv file row
    :type row: list(string)
    :param template: Template for the event description. It can contains placeholders.
    :type template: string
    :return: Nothing
    """
    event.title = row["titre"]

    event.start = convert_csv_time(row["debut2"])
    event.end = convert_csv_time(row["fin2"])
    event.registration_open_time = convert_csv_time(row["debut_internet"])
    event.registration_close_time = convert_csv_time(row["fin_internet"])
    event.num_slots = int(row["places"])
    if row["places_internet"].strip():
        event.num_online_slots = int(row["places_internet"])

    leader = User.query.filter_by(license=row["id_encadrant"]).first()
    if leader is None:
        raise Exception(f'Utilisateur {row["id_encadrant"]} inconnu')
    event.leaders = [leader]
    event.main_leader_id = leader.id

    event.description = template.format(**row,)
    event.set_rendered_description(event.description)


def convert_csv_time(date_time_str):
    """ Convert a string in csv format to a datetime object.

    :param date_time_str: Date to parse (eg: 31/12/2020 14:45).
    :type date_time_str: string
    :return: The parsed date
    :rtype: :py:class:`datetime.datetime`
    """
    return datetime.strptime(date_time_str, "%d/%m/%y %H:%M")


def process_stream(base_stream, activity_type, description):
    """ Creates the events from a csv file.

    Processing will first try to process it as an UTF8 encoded file. If it fails
    on a decoding error, it will try as Windows encoding (iso-8859-1).

    :param base_stream: the csv file as a stream.
    :type base_stream: :py:class:`io.StringIO`
    :param activity_type: The type of activity of the new events.
    :type activity_type: :py:class:`collectives.models.activitytype.ActivityType`
    :param description: Description template that will be used to generate new events
                        description.
    :type description: String
    :return: The number of processed events, and the number of failed attempts
    :rtype: (int, int)
    """
    try:
        stream = codecs.iterdecode(base_stream, "utf8")
        events, processed, failed = csv_to_events(stream, description)
    except UnicodeDecodeError:
        base_stream.seek(0)
        stream = codecs.iterdecode(base_stream, "iso-8859-1")
        events, processed, failed = csv_to_events(stream, description)

    # Complete event before adding it to db
    for event in events:
        event.activity_types = [activity_type]
        db.session.add(event)

    db.session.commit()
    return processed, failed


def csv_to_events(stream, description):
    """ Decode the csv stream to populate events.

    :param stream: the csv file as a stream.
    :type stream: :py:class:`io.StringIO`
    :param description: Description template that will be used to generate new events
                        description.
    :type description: String
    :return: The new events, the number of processed events, and the number of
            failed attempts
    :rtype: list(:py:class:`collectives.models.event.Event`), int, int
    """
    events = []
    processed = 0
    failed = []

    fields = current_app.config["CSV_COLUMNS"]
    reader = csv.DictReader(stream, delimiter=",", fieldnames=fields)
    for row in reader:
        processed += 1

        event = Event()
        try:
            fill_from_csv(event, row, description)
            events.append(event)
        except Exception as e:
            failed.append(
                f"Impossible d'importer la ligne {processed}: [{type(e).__name__}] {str(e)} {str(row)}"
            )
    return events, processed, failed
