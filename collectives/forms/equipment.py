"""Module containing forms related to equipment management
"""
from flask_wtf import FlaskForm
from datetime import datetime
from wtforms import (
    StringField,
    SubmitField,
    DateField,
    SelectField,
)
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired

from collectives.utils.numbers import FlexibleDecimalField
from ..models import Equipment, EquipmentType, EquipmentModel, photos


class EquipmentTypeForm(FlaskForm):
    """Form for adding an equipment type, specifying its name, price, deposit, and related image"""

    class Meta:
        model = EquipmentType
        only = ["type_name"]

    name = StringField(label="Type d'équipement :", validators=[DataRequired()])
    price = FlexibleDecimalField(
        label="Prix :",
        render_kw={
            "pattern": "^[0-9]+([.|,][0-9]+){0,1}$",
            "placeholder": "Prix",
        },
    )
    deposit = FlexibleDecimalField(
        label="Caution :",
        render_kw={
            "pattern": "^[0-9]+([.|,][0-9]+){0,1}$",
            "placeholder": "Caution",
        },
    )
    imageType_file = FileField(
        "Ajouter une image :", validators=[FileAllowed(photos, "Image uniquement!")]
    )
    submit = SubmitField("Enregistrer")


class EquipmentModelForm(FlaskForm):
    """Form for adding an equipment model, specifying its name and type"""

    class Meta:
        model = EquipmentModel
        only = ["name", "equipmentType"]

    name = StringField("Modèle d'équipement :")

    submit = SubmitField("Enregistrer")


class EquipmentForm(FlaskForm):
    """Form for adding an equipment, specifying its reference, model, purchase date and price"""

    class Meta:
        model = Equipment
        only = ["reference", "purchase"]

    reference = StringField("Référence de l'équipement :")

    purchaseDate = DateField("Date d'achat :", format="%d/%m/%Y", default=datetime.now())

    purchasePrice = FlexibleDecimalField("Prix d'achat :")

    equipment_model_id = SelectField("Modèle :", coerce=int, choices=[])

    manufacturer = StringField("Fabricant :")
    submit = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.equipment_model_id.choices = [
            (i.id, i.name) for i in EquipmentModel.query.all()
        ]


class DeleteForm(FlaskForm):
    """Form for deleting an equipment"""

    delete = SubmitField("Supprimer")
