"""Module for registration related classes
"""
from .globals import db
from .utils import ChoiceEnum
from flask_uploads import UploadSet, IMAGES
from sqlalchemy.orm import validates


# Upload
imgtypeequip = UploadSet("imgtypeequip", IMAGES)


class EquipmentStatus(ChoiceEnum):
    Available = 0
    Rented = 1
    Unavailable = 2
    InReview = 3
    

    @classmethod
    def display_names(cls):
        """Display name of the current status

        :return: status of the event
        :rtype: string
        """
        return {
            cls.Available: "Libre",
            cls.Rented: "Loué",
            cls.Unavailable: "Invalide",
            cls.InReview: "Révision en cours",
        }


class EquipmentType(db.Model):
    """Class of a type of equipment."""

    __tablename__ = "equipment_types"

    id = db.Column(db.Integer, primary_key=True)

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
            filename = imgtypeequip.save(file, name="type-" + str(self.name) + ".")
            print(filename)
            self.pathImg = filename



class EquipmentModel(db.Model):
    """Class of a model of equipment.
    """

    __tablename__ = "equipment_models"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    equipments = db.relationship(
        "Equipment", lazy="select", backref=db.backref("model", lazy="joined")
    )

    equipment_type_id = db.Column(db.Integer, db.ForeignKey("equipment_types.id"))


class Equipment(db.Model):
    """Class of an equipment.
    """

    __tablename__ = "equipments"
    id = db.Column(db.Integer, primary_key=True)

    reference = db.Column(db.String(100), nullable=False)

    purchaseDate = db.Column(db.DateTime, nullable=False, index=True)

    purchasePrice = db.Column(db.Float, nullable=True)

    status = db.Column(
        db.Enum(EquipmentStatus),
        nullable=False,
        default=EquipmentStatus.Available,
        info={"choices": EquipmentStatus.choices(), "coerce": EquipmentStatus.coerce},
    )

    #brand = db.Column(db.String(50), nullable = True)

    equipment_model_id = db.Column(db.Integer, db.ForeignKey("equipment_models.id"))
