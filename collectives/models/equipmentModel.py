"""Module for registration related classes
"""
from .globals import db


class EquipmentModel(db.Model):
    """Class of a model of equipment.
    An equipment is
    """

    __tablename__ = "equipment_models"

    id = db.Column(db.Integer, primary_key=True)

    model_name = db.Column(db.String(100), nullable=False)

    models = db.relationship('Equipment', lazy='select',
        backref=db.backref('equipment_model', lazy='joined'))

    type_equipment_id = db.Columns(db.Integer, db.ForeignKey("equipment_types.id"))


