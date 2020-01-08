from ..models import User, Event, db
from datetime import datetime
from flask import flash, current_app
import re, codecs, csv

class PlaceholderFiller:
    def __init__(self, row):
        self.row = row

    def __call__(self, match):
        key = match.group(1)
        if key in self.row.keys():
            return self.row[key].replace('"', '\\"').replace("\n",'\\n')
        return ''

def fill_from_csv(event, row, template):
    event.title = row['title']

    filler = PlaceholderFiller(row)
    event.description = re.sub(r'\$([\w]+?)\$', filler, template)
    event.set_rendered_description(event.description)
    event.start = convert_csv_time(row['dateStart'])
    event.end = convert_csv_time(row['dateEnd'])
    event.registration_open_time = convert_csv_time(row['registrationStart'])
    event.registration_close_time = convert_csv_time(row['registrationEnd'])
    event.num_slots = int(row['seats'])
    event.num_online_slots = int(row['internetSeats'])

    leader = User.query.filter_by(license = row['initiateur']).first()
    if leader is None:
        raise Exception(f'Utilisateur {row["initiateur"]} inconnu')
    event.leaders = [leader]


def convert_csv_time(date_time_str):
    return datetime.strptime(date_time_str, '%d/%m/%y %H:%M')

def process_stream(base_stream, activity_type, description):
    # First, we try to decode csv file as utf8
    # If it fails, we try again as Windows encoding
    try :
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
    events=[]
    processed = 0
    failed = 0

    reader = csv.DictReader( stream, delimiter=",")
    for row in reader:
        processed += 1
        event = Event()
        try:
            fill_from_csv(event, row, description)
            events.append(event)
        except Exception as e:
            failed += 1
            flash(f'Impossible d\'importer la ligne {processed+1}: [{type(e).__name__}] {str(e)} {str(row)}', 'error')
    return events, processed, failed
