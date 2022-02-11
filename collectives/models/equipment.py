"""Module for registration related classes
"""
import os
from genericpath import isfile
from flask_uploads import UploadSet, IMAGES, extension

from collectives.models.reservation import ReservationLine_Equipment
from .globals import db
from .utils import ChoiceEnum


imgtypeequip = UploadSet("imgtypeequip", IMAGES)


class EquipmentStatus(ChoiceEnum):
    """Enum listing status of an equipment"""

    Available = 0
    """ Equipment is in stock, can be rented or put under review at any time """
    Rented = 1
    """ Equipment in use is no longer in stock, can't be rented anymore, and will become available or unavaible at the end of its use """
    Unavailable = 2
    """ Equipment is unavailable, it won't change status anymore """
    InReview = 3
    """ Equipment is under review, can either become unavailable or available at end of review"""

    @classmethod
    def display_names(cls):
        """Display name of the current status.

        :return: status of the equipment
        :rtype: string
        """
        return {
            cls.Available: "Libre",
            cls.Rented: "Loué",
            cls.Unavailable: "Invalide",
            cls.InReview: "Révision en cours",
        }


class EquipmentType(db.Model):
    """Class of a type of equipment.

    An equipment type is an object with a determined name, price, image, and deposit price.
    It is related to multiple models.
    """

    __tablename__ = "equipment_types"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key.

    :type: int"""

    name = db.Column(db.String(100), nullable=False)
    """Name of this type.

    :type: string"""

    pathImg = db.Column(db.String(100), nullable=True)

    price = db.Column(db.Numeric(precision=5, scale=2))
    """Price for renting this type.

    :type: float"""

    deposit = db.Column(db.Numeric(precision=5, scale=2), nullable=True)
    """Deposit price. This is the price that will cost the user if he brokes an equipment of this type.

    :type: float"""

    models = db.relationship(
        "EquipmentModel",
        lazy="select",
        backref=db.backref("equipmentType", lazy="joined"),
        cascade="all,delete",
    )
    """ List of models associated to this type.

    :type: list(:py:class:`collectives.models.equipment.EquipmentModel`)
    """

    reservationLines = db.relationship(
        "ReservationLine", back_populates="equipmentType"
    )

    def save_typeImg(self, file):
        """Save an image as type image.

        It will both save the files into the file system and save the path into the database.
        If file is None, it will do nothing. It will use Flask-Upload to save the image.

        :param file: request param to be saved.
        :type file: :py:class:`werkzeug.datastructures.FileStorage`
        """
        if file is not None:
            pathFile = (
                "collectives/static/uploads/typeEquipmentImg/type-"
                + str(self.name)
                + "."
                + extension(file.filename)
            )
            if isfile(pathFile):
                os.remove(pathFile)
            filename = imgtypeequip.save(file, name="type-num" + str(self.id) + ".")
            self.pathImg = filename

    def nb_models(self):
        """
        :return: number of equipment models of the type
        :rtype: int
        """
        return len(self.models)

    def nb_total(self):
        """
        :return: number of total equipments of the type
        :rtype: int
        """
        nbTotal = 0
        for aModel in self.models:
            nbTotal += len(aModel.equipments)

        return nbTotal

    def nb_total_unavailable(self):
        """
        :return: number of total equipments no available of the type
        :rtype: int
        """
        nbTotalUnavailable = 0
        for aModel in self.models:
            for aEquipment in aModel.equipments:
                if aEquipment.status != EquipmentStatus.Available:
                    nbTotalUnavailable += 1

        return nbTotalUnavailable

    def nb_total_available(self):
        """
        :return: number of total equipments available of the type
        :rtype: int
        """
        return self.nb_total() - self.nb_total_unavailable()

    def get_all_equipments_availables(self):
        """
        :return: List of all the equipments available of the type
        :rtype: list[:py:class:`collectives.models.equipment.Equipment]
        """
        equiments = []
        for aModel in self.models:
            for anEquipment in aModel.equipments:
                if anEquipment.status == EquipmentStatus.Available:
                    equiments.append(anEquipment)

        return equiments


class EquipmentModel(db.Model):
    """Class of a model of equipment.
    An equipment model is an object with a determined name.
    It is related to multiple equipments and one equipment type.
    """

    __tablename__ = "equipment_models"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key.

    :type: int"""

    name = db.Column(db.String(100), nullable=False)
    """Name of this type.

    :type: string"""

    manufacturer = db.Column(db.String(50))
    """Manufacturer of this equipment.
    :type: string"""

    equipments = db.relationship(
        "Equipment",
        lazy="select",
        backref=db.backref("model", lazy="joined"),
        cascade="all,delete",
    )
    """ List of equipment associated to this model.

    :type: list(:py:class:`collectives.models.equipment.Equipment`)
    """

    equipment_type_id = db.Column(db.Integer, db.ForeignKey("equipment_types.id"))
    """ Primary key of the type to which the model is related (see  :py:class:`collectives.models.equipment.EquipmentType`)

    :type: int"""


class Equipment(db.Model):
    """Class of an equipment.

    An equipment is an object with a determined reference, purchase price, purchase date, and status.
    Status are declared in the EquipmentType enumeration.
    It is related to one equipment model.
    """

    __tablename__ = "equipments"
    id = db.Column(db.Integer, primary_key=True)
    """Database primary key.

    :type: int"""

    reference = db.Column(db.String(100), nullable=False, unique=True)
    """Reference of this equipment.

    :type: string"""

    purchaseDate = db.Column(db.DateTime, nullable=False, index=True)
    """Purchase date of this equipment.

    :type: :py:class:`datetime.datetime`"""

    purchasePrice = db.Column(db.Numeric(precision=8, scale=2), nullable=True)
    """Purchase price of this equipment.

    :type: float"""

    serial_number = db.Column(db.String(50))
    """Serial number of this equipment.
    :type: String"""

    status = db.Column(
        db.Enum(EquipmentStatus),
        nullable=False,
        default=EquipmentStatus.Available,
        info={"choices": EquipmentStatus.choices(), "coerce": EquipmentStatus.coerce},
    )
    """ Status of the equipment (available, rented...).

    :type: :py:class:`collectives.models.equipment.EquipmentStatus`"""

    # brand = db.Column(db.String(50), nullable = True)

    equipment_model_id = db.Column(db.Integer, db.ForeignKey("equipment_models.id"))
    """ Primary key of the model to which the equipment is related (see  :py:class:`collectives.models.equipment.EquipmentModel`).

    :type: int"""

    reservationLines = db.relationship(
        "ReservationLine",
        secondary=ReservationLine_Equipment,
        back_populates="equipments",
    )

    def get_reservations(self):
        """
        :return: List of all the reservations related to this equipment
        :rtype: list[:py:class:`collectives.models.reservation.Reservation]
        """
        reservations = []
        for aReservationLine in self.reservationLines:
            reservations.append(aReservationLine.reservation)

        return reservations

    def is_rented(self):
        """
        :return: True if the equipment is rented
        :rtype: bool"""
        return self.status == EquipmentStatus.Rented

    def set_status_to_rented(self):
        """
        :return: True if the equipment has been set to rented
        :rtype: bool"""
        if self.is_available():
            self.status = EquipmentStatus.Rented
            return True
        return False

    def set_status_to_available(self):
        """
        :return: True if the equipment has been set to Available
        :rtype: bool"""
        self.status = EquipmentStatus.Available
        return True

    def is_available(self):
        """
        :return: True if the equipment is Available
        :rtype: bool"""
        return self.status == EquipmentStatus.Available
