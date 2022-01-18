import random,string
from collectives.models import db
from datetime import datetime
from collectives.models.reservation import ReservationStatus, Reservation


FLASK_DEBUG = False
FLASK_APP="collectives:create_app"
ADMINPWD = "foobar22"
SECRET_KEY = "".join([random.choice(string.printable) for _ in range(24)])

def create_demo_values():
    """
    Initiate the DB : put fake data to simulate what the pages would look like
    """
    reservations = [
        ["12/01/22", "21/01/22", ReservationStatus.Ongoing, False, 1, 1],
        ["01/01/22", "22/01/22", ReservationStatus.Ongoing, True, 2, 0],
        ["12/01/22", None, ReservationStatus.Planned, False, 3, 1],
        ["30/12/21", "10/01/22", ReservationStatus.Completed, False, 1, 0],
    ]

    for resi in reservations:
        res = Reservation()
        res.collect_date = datetime.strptime(resi[0], "%d/%m/%y")
        if resi[1] != None:
            res.return_date = datetime.strptime(resi[1], "%d/%m/%y")
        res.status = resi[2]
        res.extended = resi[3]
        res.user_id = resi[4]
        res.event_id = resi[5]
        db.session.add(res)
        db.session.commit()
