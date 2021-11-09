from .globals import db
from .utils import ChoiceEnum

class ReservationStatus(ChoiceEnum):
    Booked = 0
    Pending = 1
    Done = 2
    Cancelled = 3

    @classmethod
    def display_names(cls):
        """Display name of the current status

        :return: status of the event
        :rtype: string
        """
        return {
            cls.Booked: "Réservé",
            cls.Pending: "En cours",
            cls.Done:"Terminée",
            cls.Cancelled: "Annulée",
        }

class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    collect_date = db.Column(db.DateTime, nullable=False, index=True)
    return_date = db.Column(db.DateTime, nullable=False, index=True)
    is_extented = db.Column(db.Boolean, nullable = False, default = False, index=False)
    is_self = db.Column(db.Boolean, nullable=False, default=True)
    
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    lines = db.relationship('ReservationLine', lazy='select',
        backref=db.backref('line_reservation', lazy='joined'))

    status = db.Column(
        db.Enum(ReservationStatus),
        nullable=False,
        default=ReservationStatus.Booked,
        info={"choices": ReservationStatus.choices(), "coerce": ReservationStatus.coerce},
    )

class ReservationLine(db.Model):
    __tablename__ = "reservationLines"
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, index=False, default=1)
    
    equipment_type_id = db.Column(db.Integer, db.ForeignKey("equipment_types.id"), index=True, nullable=False)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.id"), index=True, nullable=False)
