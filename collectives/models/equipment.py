"""Module for registration related classes
"""
from .globals import db

class EquipmentType(db.Model):
    """Class of a type of equipment equipment.
    """

    __tablename__ = "equipment_types"

    id = db.Column(db.Integer, primary_key=True)

    type_name = db.Column(db.String(100), nullable=False)

    price = db.Column(db.Float, primary_key=True)

    models = db.relationship('EquipmentModel', lazy='select',
        backref=db.backref('type_equipment', lazy='joined'))


class EquipmentModel(db.Model):
    """Class of a model of equipment.
    An equipment is
    """

    __tablename__ = "equipment_models"

    id = db.Column(db.Integer, primary_key=True)

    model_name = db.Column(db.String(100), nullable=False)

    models = db.relationship('Equipment', lazy='select',
        backref=db.backref('equipment_model', lazy='joined'))

    type_equipment_id = db.Column(db.Integer, db.ForeignKey("equipment_types.id"))



class Equipment(db.Model):
    """Class of an equipment.
    An equipment is
    """

    __tablename__ = "equipments"

    id = db.Column(db.Integer, primary_key=True)

    purchaseDate = db.Column(db.DateTime, nullable=False, index=True)

    reference = db.Column(db.String(100), nullable=False)

    caution = db.Column(db.Float, nullable=True)

    purchasePrice = db.Column(db.Float, nullable=True)

    # idStock = db.Column(db.Integer, db.ForeignKey("stock.id"))

    equipment_model_id = db.Column(db.Integer, db.ForeignKey("equipment_models.id"))
