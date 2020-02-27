from ..models import User, Event, db
from datetime import datetime
from flask import flash, current_app
import re
import codecs
import csv


def fill_from_csv(event, row, template):
    print(row, flush=True)
    event.title = row['titre']

    event.start = convert_csv_time(row['debut2'])
    event.end = convert_csv_time(row['fin2'])
    event.registration_open_time = convert_csv_time(row['debut_internet'])
    event.registration_close_time = convert_csv_time(row['fin_internet'])
    event.num_slots = int(row['places'])
    event.num_online_slots = int(row['places_internet'])

    leader = User.query.filter_by(license=row['id_encadrant']).first()
    if leader is None:
        raise Exception(f'Utilisateur {row["id_encadrant"]} inconnu')
    event.leaders = [leader]

    event.description = template.format(**row,
    )
    event.set_rendered_description(event.description)

def convert_csv_time(date_time_str):
    return datetime.strptime(date_time_str, '%d/%m/%y %H:%M')


def process_stream(base_stream, activity_type, description):
    # First, we try to decode csv file as utf8
    # If it fails, we try again as Windows encoding
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
    events = []
    processed = 0
    failed = []

    fields = current_app.config['CSV_COLUMNS']
    reader = csv.DictReader(stream, delimiter=",", fieldnames=fields)
    for row in reader:
        processed += 1

        event = Event()
        try:
            fill_from_csv(event, row, description)
            events.append(event)
        except Exception as e:
            failed.append(
                f'Impossible d\'importer la ligne {processed}: [{type(e).__name__}] {str(e)} {str(row)}')
    return events, processed, failed
