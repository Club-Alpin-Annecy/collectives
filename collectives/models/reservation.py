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

    def is_full(self):
        """
        :return: True if the reservation line is full
        :rtype: bool"""
        return self.quantity <= len(self.equipments)

    def add_equipment(self, equipment):
        """
        :return: True the equipment has been added well
        :rtype: bool"""
        if not self.is_full():
            if equipment.set_status_to_rented():
                self.equipments.append(equipment)
                return True
        return False

    def remove_equipment(self, equipment):
        """
        :return: True the equipment has been removed well
        :rtype: bool"""
        if equipment in self.equipments:
            self.equipments.remove(equipment)
            equipment.set_status_to_available()
            return True
        return False

    def remove_equipment_decreasing_quantity(self, equipment):
        """
        :return: True the equipment has been removed well
        :rtype: bool"""
        if self.remove_equipment(equipment):
            self.quantity -= 1
            return True
        return False

    def add_equipment_by_increasing_quantity(self, equipment):
        """
        :return: True the equipment has been added well
        :rtype: bool"""
        if self.is_full():
            self.quantity += 1
        return self.add_equipment(equipment)

    def get_equipments_rented(self):
        """
        :return: List of all the equipments Rented
        :rtype: list[:py:class:`collectives.models.equipment.Equipment]
        """
        equipmentsRented = []
        for equipment in self.equipments:
            if equipment.is_rented():
                equipmentsRented.append(equipment)
        return equipmentsRented

    def get_equipments_returned(self):
        """
        :return: List of all the equipments available
        :rtype: list[:py:class:`collectives.models.equipment.Equipment]
        """
        equipmentsAvailable = []
        for equipment in self.equipments:
            if equipment.is_available():
                equipmentsAvailable.append(equipment)
        return equipmentsAvailable

    def count_equipments_returned(self):
        """
        :return: Number of equipments returned
        :rtype: Int
        """
        return len(self.get_equipments_returned())

    def count_equipments(self):
        """
        :return: Number of equipments in the reservation
        :rtype: Int
        """
        return len(self.equipments)

    def get_ratio_equipments(self):
        """
        :return: Number of equipments in each reservation line
        :rtype: String
        """
        if self.reservation.is_ongoing():
            return (
                str(self.count_equipments_returned())
                + "/"
                + str(self.count_equipments())
            )
        return str(self.count_equipments()) + "/" + str(self.quantity)


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

    event = db.relationship("Event", back_populates="reservations")

    lines = db.relationship(
        "ReservationLine",
        lazy="select",
        backref=db.backref("reservation", lazy="joined"),
        cascade="all,delete",
    )
    """ List of lines of the reservation.

    :type: list(:py:class:`collectives.models.reservation.ReservationLine`)
    """

    def is_planned(self):
        """
        :return: True if the reservation is Planned
        :rtype: bool"""
        return self.status == ReservationStatus.Planned

    def is_ongoing(self):
        """
        :return: True if the reservation is Ongoing
        :rtype: bool"""
        return self.status == ReservationStatus.Ongoing

    def is_completed(self):
        """
        :return: True if the reservation is Completed
        :rtype: bool"""
        return self.status == ReservationStatus.Completed

    def is_full(self):
        """
        :return: True if the reservation is full
        :rtype: bool"""
        for reservationLine in self.lines:
            if not reservationLine.is_full():
                return False
        return True

    def count_equipments_returned(self):
        """
        :return: Number of equipments returned
        :rtype: Int
        """
        nb_equipments_rendered = 0
        for reservationLine in self.lines:
            nb_equipments_rendered += reservationLine.count_equipments_returned()
        return nb_equipments_rendered

    def count_equipments(self):
        """
        :return: Number of equipments in each reservation line
        :rtype: Int
        """
        nb_equipments = 0
        for reservationLine in self.lines:
            nb_equipments += reservationLine.count_equipments()
        return nb_equipments

    def count_total_quantity(self):
        """
        :return: total of quantity in each reservation line
        :rtype: Int
        """
        quantity = 0
        for reservationLine in self.lines:
            quantity += reservationLine.quantity
        return quantity

    def get_ratio_equipments(self):
        """
        :return: Number of equipments in each reservation line
        :rtype: String
        """
        if self.is_ongoing():
            return (
                str(self.count_equipments_returned())
                + "/"
                + str(self.count_equipments())
            )
        return str(self.count_equipments()) + "/" + str(self.count_total_quantity())

    def can_be_completed(self):
        """
        :return: True if the reservation is all the equipments rented are returned
        :rtype: bool"""
        return self.count_equipments_returned() == self.count_equipments()

    def get_line_of_type(self, equipmentType):
        """
        :return: the line containing the type
        :rtype: list[:py:class:`collectives.models.reservation.ReservationLine]
        """
        for reservationLine in self.lines:
            if reservationLine.equipmentType == equipmentType:
                return reservationLine
        return None

    def get_or_create_line_of_type(self, equipmentType):
        """
        :return: the line containing the type
        :rtype: list[:py:class:`collectives.models.reservation.ReservationLine]
        """
        reservationLine = self.get_line_of_type(equipmentType)
        if not reservationLine:
            reservationLine = ReservationLine()
            reservationLine.quantity = 0
            reservationLine.equipmentType = equipmentType
            self.lines.append(reservationLine)
        return reservationLine

    def add_equipment(self, equipment):
        """
        :return: True the equipment has been added well
        :rtype: bool"""
        if equipment:
            reservationLine = self.get_or_create_line_of_type(
                equipment.model.equipmentType
            )
            return reservationLine.add_equipment_by_increasing_quantity(equipment)

        return False

    def get_equipments(self):
        """
        :return: the line containing the type
        :rtype: list[:py:class:`collectives.models.reservation.ReservationLine]
        """
        equipments = []
        for reservationLine in self.lines:
            equipments.extend(reservationLine.equipments)
        return equipments

    def set_user(self, user):
        """
        :return: True the equipment has been added well
        :rtype: bool"""
        if user:
            self.user = user
            return True
        return False

    def remove_equipment_decreasing_quantity(self, equipment):
        """
        :return: True the equipment has been removed well
        :rtype: bool"""
        if equipment:
            line = self.get_line_of_type(equipment.model.equipmentType)
            if (
                line.remove_equipment_decreasing_quantity(equipment)
                and line.quantity == 0
            ):
                self.lines.remove(line)
                return True
        return False
