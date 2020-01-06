from ..models import User
from datetime import datetime
from flask import current_app
import re

class PlaceholderFiller:
    def __init__(self, row):
        self.row = row

    def __call__(self, match):
        key = match.group(1)
        if key in self.row.keys():
            return self.row[key].replace('"', '\\"').replace("\n",'\\n')
        return ''

def fill_from_csv(event, row):
            event.title = row['title']

            filler = PlaceholderFiller(row)
            template = current_app.config['DESCRIPTION_TEMPLATE']
            event.description = re.sub(r'\$([\w]+?)\$', filler, template)
            event.set_rendered_description(event.description)
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
