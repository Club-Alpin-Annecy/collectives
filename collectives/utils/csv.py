""" Module to handle csv import
"""
import builtins
from datetime import datetime, timedelta
import codecs
import csv

from flask import current_app

from collectives.models import User, Event, EventTag, db
from collectives.models.user_group import GroupEventCondition, UserGroup
from collectives.utils.time import format_date


def fill_from_csv(event, row, template):
    """Fill an Event object attributes with parameter from a csv row.

    :param event: The evet object to populate.
    :type event: :py:class:`collectives.models.event.Event`
    :param row: List of value from a csv file row
    :type row: list(string)
    :param template: Template for the event description. It can contains placeholders.
    :type template: string
    :return: Nothing
    """

    event.title = parse(row, "titre")

    # Subscription dates and slots
    event.start = parse(row, "debut")
    event.end = parse(row, "fin")
    event.num_slots = parse(row, "places")

    parent_event_id = parse(row, "parent")
    if parent_event_id != "":
        if Event.query.get(parent_event_id) is None:
            raise builtins.Exception(f"La collective {parent_event_id} n'existe pas")
        event.user_group = UserGroup()
        event.user_group.event_conditions.add(
            GroupEventCondition(event_id=parent_event_id, is_leader=False)
        )

    # Online subscription dates and slots
    if row["places_internet"].strip():
        event.num_online_slots = parse(row, "places_internet")
        if event.num_online_slots > event.num_slots:
            raise builtins.Exception(
                "Le nombre de places par internet doit être inférieur au nombre de places de "
                "la collective"
            )
        if row["debut_internet"] != None and row["debut_internet"].strip():
            event.registration_open_time = parse(row, "debut_internet")
        else:
            # Set default value
            event.registration_open_time = (
                event.start
                - timedelta(days=current_app.config["REGISTRATION_OPENING_DELTA_DAYS"])
            ).replace(
                hour=current_app.config["REGISTRATION_OPENING_HOUR"],
                minute=0,
            )
        if row["fin_internet"] != None and row["fin_internet"].strip():
            event.registration_close_time = parse(row, "fin_internet")
        else:
            # Set default value
            event.registration_close_time = (
                event.start
                - timedelta(days=current_app.config["REGISTRATION_CLOSING_DELTA_DAYS"])
            ).replace(
                hour=current_app.config["REGISTRATION_CLOSING_HOUR"],
                minute=0,
            )

    # Description
    parse(row, "altitude")
    parse(row, "denivele")
    parse(row, "distance")
    event.description = template.format(**row)
    event.set_rendered_description(event.description)

    # Event tag
    tag_id = EventTag.get_type_from_csv_code(parse(row, "tag"))
    if tag_id is not None:
        tag = EventTag(tag_id=tag_id)
        event.tag_refs.append(tag)

    # Leader
    leader = User.query.filter_by(license=row["id_encadrant"]).first()
    if leader is None:
        raise builtins.Exception(
            f"L'encadrant {row['nom_encadrant']} (numéro de licence {row['id_encadrant']}) n'a "
            "pas encore créé de compte"
        )

    # Check if event already exists in same activity
    if Event.query.filter_by(
        main_leader_id=leader.id, title=event.title, start=event.start
    ).first():
        raise builtins.Exception(
            f"La collective {event.title} démarrant le {format_date(event.start)} et encadrée "
            f"par {row['nom_encadrant']} existe déjà."
        )

    event.leaders = [leader]
    event.main_leader_id = leader.id


def parse(row, column_name):
    """Parse a column value in csv format to an object depending on column type.
    Raise an exception if field is mandatory and is not set

    :param row: List of value from a csv file row
    :type row: list(string)
    :param string column_name: Column name
    :return: The parsed value
    """
    csv_columns = current_app.config["CSV_COLUMNS"]
    column_short_desc = csv_columns[column_name]["short_desc"]

    if row[column_name] is None:
        raise builtins.Exception(
            f"La colonne '{column_short_desc}' n'existe pas dans le fichier"
        )

    value_str = row[column_name].strip()

    # Check if mandatory column is well set
    if not value_str and not csv_columns[column_name].get("optional", 0):
        raise builtins.Exception(
            f"La colonne '{column_short_desc}' est obligatoire et n'est pas renseignée"
        )

    column_type = csv_columns[column_name]["type"]
    if column_type == "datetime":
        try:
            return datetime.strptime(value_str, "%d/%m/%Y %H:%M")
        except ValueError as err:
            raise builtins.Exception(
                f"La date '{value_str}' de la colonne '{column_short_desc}' n'est pas dans le "
                "bon format jj/mm/yyyy hh:mm (ex: 31/12/2020 14:45)"
            ) from err
    elif column_type == "int":
        if value_str:
            try:
                return int(value_str)
            except ValueError as err:
                raise builtins.Exception(
                    f"La valeur '{value_str}' de la colonne '{column_name}' doit être un "
                    "nombre entier"
                ) from err

    return value_str


def process_stream(base_stream, activity_type, description):
    """Creates the events from a csv file.

    Processing will first try to process it as an UTF8 encoded file. If it fails
    on a decoding error, it will try as Windows encoding (iso-8859-1).

    :param base_stream: the csv file as a stream.
    :type base_stream: :py:class:`io.StringIO`
    :param activity_type: The type of activity of the new events.
    :type activity_type: :py:class:`collectives.models.activity_type.ActivityType`
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
    """Decode the csv stream to populate events.

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
    fields = list(current_app.config["CSV_COLUMNS"].keys())

    reader = csv.DictReader(stream, delimiter=",", fieldnames=fields)
    next(reader, None)  # skip the headers
    for row in reader:
        processed += 1

        event = Event()
        try:
            fill_from_csv(event, row, description)
            events.append(event)
        # pylint: disable=broad-except
        except builtins.Exception as ex:
            failed.append(
                f"Impossible d'importer la ligne {processed+1}: [{type(ex).__name__}] {str(ex)}"
            )
        # pylint: enable=broad-except
    return events, processed, failed
