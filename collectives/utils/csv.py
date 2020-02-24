from ..models import User, Event, db
from datetime import datetime
from flask import flash, current_app
import re
import codecs
import csv


# COLUMN NAME
LEADER=1
TITLE=10
START=4
END=6
REGISTRATION_START=7
REGISTRATION_END=8
ALTITUDE=13
DENIVELE=14
COTATION=15
OBSERVATIONS=17
SLOTS=18
INTERNET_SLOTS=19



def fill_from_csv(event, row, template):
    print(row, flush=True)
    event.title = row[TITLE]

    event.start = convert_csv_time(row[START])
    event.end = convert_csv_time(row[END])
    event.registration_open_time = convert_csv_time(row[REGISTRATION_START])
    event.registration_close_time = convert_csv_time(row[REGISTRATION_END])
    event.num_slots = int(row[SLOTS])
    event.num_online_slots = int(row[INTERNET_SLOTS])

    leader = User.query.filter_by(license=row[LEADER]).first()
    if leader is None:
        raise Exception(f'Utilisateur {row[LEADER]} inconnu')
    event.leaders = [leader]

    event.description = template.format(altitude = row[ALTITUDE],
        denivele = row[DENIVELE],
        cotation = row[COTATION],
        observations = row[OBSERVATIONS],
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

    reader = csv.reader(stream, delimiter=",")
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
