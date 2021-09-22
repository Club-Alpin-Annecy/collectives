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
