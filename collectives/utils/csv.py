from ..models import User, Event, db
from datetime import datetime
import json, csv, codecs
from flask import flash

def fill_from_csv(event, row):
            event.title = row['title']
            event.rendered_description = row['observations']
            event.description = json.dumps({'ops':[{'insert': row['observations'] }]})
            event.start = convert_csv_time(row['dateStart'])
            event.end = convert_csv_time(row['dateEnd'])
            event.registration_open_time = convert_csv_time(row['registrationStart'])
            event.registration_close_time = convert_csv_time(row['registrationEnd'])
            event.num_slots = int(row['seats'])
            event.num_online_slots = int(row['internetSeats'])

            leader = User.query.filter_by(license = row['initiateur']).first()
            if leader == None:
                raise Exception(f'Utilisateur {row["initiateur"]} inconnu')
            event.leaders = [leader]


def convert_csv_time(date_time_str):
    return datetime.strptime(date_time_str, '%d/%m/%y %H:%M')

def process_stream(base_stream, activity_type):
    # First, we try to decode csv file as utf8
    # If it fails, we try again as Windows encoding
    try :
        stream = codecs.iterdecode(base_stream, "utf8")
        events, processed, failed = csv_to_events(stream)
    except UnicodeDecodeError:
        base_stream.seek(0)
        stream = codecs.iterdecode(base_stream, "iso-8859-1")
        events, processed, failed = csv_to_events(stream)

    # Complete event before adding it to db
    for event in events:
        event.activity_types = [activity_type]
        db.session.add(event)

    db.session.commit()
    return processed, failed

def csv_to_events(stream):
    events=[]
    processed = 0
    failed = 0

    reader = csv.DictReader( stream, delimiter=",")
    for row in reader:
        processed += 1
        event = Event()
        try:
            fill_from_csv(event, row)
            events.append(event)
        except Exception as e:
            failed += 1
            flash(f'Impossible d\'importer la ligne {processed+1}: [{type(e).__name__}] {str(e)} {str(row)}', 'error')
    return events, processed, failed
