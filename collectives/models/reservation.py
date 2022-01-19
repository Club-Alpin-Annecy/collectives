"""Module for registration related classes
"""

from datetime import datetime
from sqlalchemy import CheckConstraint
from .globals import db
from .utils import ChoiceEnum


class ReservationStatus(ChoiceEnum):
    """Enum listing status of an reservation"""

    Planned = 0
    """ Reservation is planned, equipment related to this reservation is locked"""
    Ongoing = 1
    """ Reservation is ongoing"""
    Completed = 2
    """ Equipment is done, it won't change status anymore"""
    Cancelled = 3
    """ Reservation has been cancelled"""

    @classmethod
    def display_names(cls):
        """Display name of the current status.

        :return: status of the reservation
        :rtype: string
        """
        return {
            cls.Planned: "Prévue",
            cls.Ongoing: "En cours",
            cls.Completed: "Terminée",
            cls.Cancelled: "Annulée",
        }


ReservationLine_Equipment = db.Table(
    "reservation_lines_equipments",
    db.metadata,
    db.Column(
        "reservation_line_id", db.ForeignKey("reservation_lines.id"), primary_key=True
    ),
    db.Column("equipment_id", db.ForeignKey("equipments.id"), primary_key=True),
)


class ReservationLine(db.Model):
    """Class of an reservation line.

    An reservation line is an object with a determined quantity.
    It is related to a reservation and an equipment.
    """

    __tablename__ = "reservation_lines"
    id = db.Column(db.Integer, primary_key=True)
    """Database primary key.

    :type: int"""

    quantity = db.Column(db.Integer, nullable=False, default=1)
    """Quantity of equipment.

    :type: int"""

    CheckConstraint("quantity >= 0", name="CK_RESERVATION_quantity")

    equipments = db.relationship(
        "Equipment",
        secondary=ReservationLine_Equipment,
        back_populates="reservationLines",
    )
    """ List of equipments of a line of reservation.

    :type: list(:py:class:`collectives.models.equipment.Equipment`)
    """

    equipmentType = db.relationship("EquipmentType", back_populates="reservationLines")
    """ Equipments of a line of reservation.

    :type: list(:py:class:`collectives.models.equipment.EquipmentType`)
    """

    equipment_type_id = db.Column(db.Integer, db.ForeignKey("equipment_types.id"))
    """ Primary key of the related equipment type (see  :py:class:`collectives.models.equipment.EquipmentType`).
    :type: int"""

    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.id"))
    """ Primary key of the related reservation (see  :py:class:`collectives.models.reservation.Reservation`).
    :type: int"""

    def is_not_full(self):
        """
        :return: True if the reservation line is not full
        :rtype: bool"""
        print(self.equipments)
        return self.quantity > len(self.equipments)


class Reservation(db.Model):
    """Class of an reservation.

    An reservation is an object with a determined collection date, return date, and status.
    Status are declared in the :py:class:`collectives.models.reservation.ReservationStatus` enumeration.
    It is related to many reservation lines (each equipment and it's quantity), to a user, and an optional event.
    """

    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    """Database primary key.

    :type: int"""

    collect_date = db.Column(
        db.DateTime, nullable=False, index=True, default=datetime.now()
    )
    """Date to which user has to retrieve his equipment.

    :type: :py:class:`datetime.datetime`"""

    return_date = db.Column(db.DateTime, index=True)
    """Date to which user has to give back his equipment.

    :type: :py:class:`datetime.datetime`"""

    status = db.Column(
        db.Enum(ReservationStatus),
        nullable=False,
        default=ReservationStatus.Planned,
        info={
            "choices": ReservationStatus.choices(),
            "coerce": ReservationStatus.coerce,
        },
    )
    """ Status of the reservation (planned, ongoing...).

    :type: :py:class:`collectives.models.reservation.ReservationStatus`"""

    extended = db.Column(db.Boolean, nullable=False, default=False)
    """ Whether this reservation is extended (return date has been delayed)

    :type: bool"""

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    """ Primary key of the related user (see  :py:class:`collectives.models.user.User`).
    :type: int"""

    user = db.relationship("User", back_populates="reservations")

    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    """ Primary key of the related user (see  :py:class:`collectives.models.event.Event`).
    :type: int"""

    lines = db.relationship(
        "ReservationLine",
        lazy="select",
        backref=db.backref("reservation", lazy="joined"),
        cascade="all,delete",
    )
    """ List of lines of the reservation.

    :type: list(:py:class:`collectives.models.reservation.ReservationLine`)
    """
