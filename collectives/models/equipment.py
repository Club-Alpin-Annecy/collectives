"""Module for registration related classes
"""
import os
from genericpath import isfile
from flask_uploads import UploadSet, IMAGES, extension
from .globals import db
from .utils import ChoiceEnum


# Upload
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
        """Display name of the current status

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
    """Database primary key

    :type: int"""

    name = db.Column(db.String(100), nullable=False)

    pathImg = db.Column(db.String(100), nullable=True)

    price = db.Column(db.Float)

    deposit = db.Column(db.Float, nullable=True)

    models = db.relationship(
        "EquipmentModel",
        lazy="select",
        backref=db.backref("equipmentType", lazy="joined"),
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
            filename = imgtypeequip.save(file, name="type-" + str(self.name) + ".")
            self.pathImg = filename

    def nbModels(self):
        """
        :return: number of equipment models of the type
        :rtype: int
        """
        return len(self.models)


class EquipmentModel(db.Model):
    """Class of a model of equipment.
    An equipment model is an object with a determined name.
    It is related to multiple equipments and one equipment type.
    """

    __tablename__ = "equipment_models"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    name = db.Column(db.String(100), nullable=False)

    equipments = db.relationship(
        "Equipment", lazy="select", backref=db.backref("model", lazy="joined")
    )

    equipment_type_id = db.Column(db.Integer, db.ForeignKey("equipment_types.id"))


class Equipment(db.Model):
    """Class of an equipment.

    An equipment is an object with a determined reference, purchase price, purchase date, and status.
    Status are declared in the EquipmentType enumeration.
    It is related to one equipment model.
    """

    __tablename__ = "equipments"
    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""
    
    reference = db.Column(db.String(100), nullable=False)

    purchaseDate = db.Column(db.DateTime, nullable=False, index=True)

    purchasePrice = db.Column(db.Float, nullable=True)

    status = db.Column(
        db.Enum(EquipmentStatus),
        nullable=False,
        default=EquipmentStatus.Available,
        info={"choices": EquipmentStatus.choices(), "coerce": EquipmentStatus.coerce},
    )

    # brand = db.Column(db.String(50), nullable = True)

    equipment_model_id = db.Column(db.Integer, db.ForeignKey("equipment_models.id"))
