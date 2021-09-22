"""Module for registration related classes
"""
from .globals import db


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

    idStock = db.Columns(db.Integer, db.ForeignKey("stock.id"))

    equipment_model_id = db.Columns(db.Integer, db.ForeignKey("equipment_models.id"))
