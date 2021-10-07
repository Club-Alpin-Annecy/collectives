"""Module for registration related classes
"""
from .globals import db
from .utils import ChoiceEnum

class EquipmentStatus(ChoiceEnum):
    Available = 0
    Booked = 1
    Rented = 2
    Unavailable = 3
    pendingReview = 4
    

    @classmethod
    def display_names(cls):
        """Display name of the current status

        :return: status of the event
        :rtype: string
        """
        return {
            cls.Confirmed: "Confirmée",
            cls.Pending: "En attente",
            cls.Cancelled: "Annulée",
        }


class EquipmentType(db.Model):
    """Class of a type of equipment equipment."""

    __tablename__ = "equipment_types"

    id = db.Column(db.Integer, primary_key=True)

    type_name = db.Column(db.String(100), nullable=False)

    price = db.Column(db.Float)

    models = db.relationship(
        "EquipmentModel",
        lazy="select",
        backref=db.backref("type_equipment", lazy="joined"),
    )


class EquipmentModel(db.Model):
    """Class of a model of equipment.
    An equipment is
    """

    __tablename__ = "equipment_models"

    id = db.Column(db.Integer, primary_key=True)

    model_name = db.Column(db.String(100), nullable=False)

    models = db.relationship(
        "Equipment", lazy="select", backref=db.backref("equipment_model", lazy="joined")
    )

    type_equipment_id = db.Column(db.Integer, db.ForeignKey("equipment_types.id"))


class Equipment(db.Model):
    """Class of an equipment.
    An equipment is
    """

    __tablename__ = "equipments"
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), nullable=False)
    caution = db.Column(db.Float, nullable=True)
    lastReview = db.Column(db.DateTime, nullable = True)
    purchaseDate = db.Column(db.DateTime, nullable=False, index=True)
    purchasePrice = db.Column(db.Float, nullable=True)
    brand = db.Column(db.String(50), nullable = True)



    equipment_model_id = db.Column(db.Integer, db.ForeignKey("equipment_models.id"))
