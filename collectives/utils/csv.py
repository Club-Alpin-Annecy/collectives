""" Module to handle csv import
"""
from datetime import datetime, timedelta
import codecs
import csv

from flask import current_app

from ..context_processor import helpers_processor
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

    csv_columns = current_app.config["CSV_COLUMNS"]

    mandatory_column(row["titre"], csv_columns.get("titre")["short_desc"]),
    event.title = row["titre"].strip()

    # Subscription dates and slots
    event.start = convert_csv_time(
        row["debut"], csv_columns.get("debut")["short_desc"], True
    )
    event.end = convert_csv_time(row["fin"], csv_columns.get("fin")["short_desc"], True)
    event.num_slots = convert_csv_int(
        row["places"], csv_columns.get("places")["short_desc"], True
    )

    # Online subscription dates and slots
    if row["places_internet"].strip():
        event.num_online_slots = convert_csv_int(
            row["places_internet"], csv_columns.get("places_internet")["short_desc"]
        )
        if event.num_online_slots > event.num_slots:
            raise Exception(
                "Le nombre de places par internet doit être inférieur au nombre de places de la collective"
            )
        event.registration_open_time = (
            convert_csv_time(
                row["debut_internet"], csv_columns.get("debut_internet")["short_desc"]
            )
            if row["debut_internet"] != None and row["debut_internet"].strip()
            else (event.start - timedelta(days=7)).replace(hour=7, minute=00)
        )
        event.registration_close_time = (
            convert_csv_time(
                row["fin_internet"], csv_columns.get("fin_internet")["short_desc"]
            )
            if row["debut_internet"] != None and row["fin_internet"].strip()
            else (event.start - timedelta(days=1)).replace(hour=18, minute=00)
        )

    # Description
    convert_csv_int(row["altitude"], csv_columns.get("altitude")["short_desc"])
    convert_csv_int(row["denivele"], csv_columns.get("denivele")["short_desc"])
    convert_csv_int(row["distance"], csv_columns.get("distance")["short_desc"])
    event.description = template.format(**row,)
    event.set_rendered_description(event.description)

    # Leader
    leader = User.query.filter_by(license=row["id_encadrant"]).first()
    if leader is None:
        raise Exception(
            "L'encadrant {} (numéro de licence {}) n'a pas encore créé de compte".format(
                row["nom_encadrant"], row["id_encadrant"]
            )
        )

    # Check if event already exists in same activity
    if Event.query.filter_by(
        main_leader_id=leader.id, title=event.title, start=event.start
    ).first():
        raise Exception(
            "La collective {} démarrant le {} et encadrée par {} existe déjà.".format(
                event.title,
                helpers_processor()["format_date"](event.start),
                row["nom_encadrant"],
            )
        )

    event.leaders = [leader]
    event.main_leader_id = leader.id


def convert_csv_time(date_time_str, column_name, mandatory=False):
    """ Convert a string in csv format to a datetime object.
    Raise an exception if field is mandatory and is not set

    :param string date_time_str: Date to parse (eg: 31/12/2020 14:45).
    :param string column_name: Column name
    :param boolean mandatory: Set if column value is mandatory
    :return: The parsed date
    :rtype: :py:class:`datetime.datetime`
    """
    if mandatory:
        mandatory_column(date_time_str, column_name)
    try:
        return datetime.strptime(date_time_str, "%d/%m/%Y %H:%M")
    except ValueError as e:
        raise Exception(
            "La date '{}' de la colonne '{}' n'est pas dans le bon format jj/mm/yyyy hh:mm (ex: 31/12/2020 14:45)".format(
                date_time_str, column_name
            )
        )


def convert_csv_int(value_str, column_name, mandatory=False):
    """ Convert a sting in csv format to an integer
    Raise an exception if field is mandatory and is not set

    :param string value_str: Integer to parse
    :param string column_name: Column name
    :param boolean mandatory: Set if column value is mandatory
    :return: The parsed integer
    :rtype: int`
    """
    if mandatory:
        mandatory_column(value_str, column_name)
    if value_str.strip():
        try:
            return int(value_str)
        except ValueError as e:
            raise Exception(
                "La valeur '{}' de la colonne '{}' doit être un entier".format(
                    value_str, column_name
                )
            )


def mandatory_column(value_str, column_name):
    """ Raise an exception if mandatory field is not defined

    :param string value_str: Value to check
    :param string column_name: Column name
    """
    if not value_str.strip():
        raise Exception(
            "La colonne '{}' est obligatoire et n'est pas renseignée".format(
                column_name
            )
        )


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
    fields = []
    reader = csv.DictReader(
        stream, delimiter=",", fieldnames=[*current_app.config["CSV_COLUMNS"]]
    )
    next(reader, None)  # skip the headers
    for row in reader:
        processed += 1

        event = Event()
        try:
            fill_from_csv(event, row, description)
            events.append(event)
        except Exception as e:
            failed.append(
                f"Impossible d'importer la ligne {processed+1}: [{type(e).__name__}] {str(e)}"
            )
    return events, processed, failed
