from ..models import User
from datetime import datetime
import json

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
