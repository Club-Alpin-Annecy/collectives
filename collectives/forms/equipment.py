"""Module containing forms related to equipment management
"""
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, SelectField, HiddenField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelForm
from collectives.utils.numbers import FlexibleDecimalField
from .validators import UniqueValidator
from ..models import Equipment, EquipmentType, EquipmentModel, photos, db


class EquipmentTypeForm(FlaskForm, ModelForm):
    """Form for adding an equipment type, specifying its name, price, deposit, and related image"""

    name = StringField(label="Type d'équipement :", validators=[DataRequired()])
    reference_prefix = StringField(
        label="Préfixe de la référence :",
        validators=[
            DataRequired(),
            UniqueValidator(
                EquipmentType.reference_prefix, get_session=lambda: db.session
            ),
        ],
    )
    price = FlexibleDecimalField(
        label="Prix :",
        render_kw={
            "pattern": "^[0-9]+([.|,][0-9]+){0,1}$",
            "placeholder": "Prix",
            "title":"Utilisez uniquement des chiffres",
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
        only = ["name", "equipmentType", "manufacturer"]

    name = StringField("Modèle d'équipement :")
    manufacturer = StringField(label="Fabricant :", validators=[DataRequired()])
    submit = SubmitField("Enregistrer")


class EquipmentForm(FlaskForm):
    """Form for adding an equipment, specifying its reference, model, purchase date and price"""

    class Meta:
        model = Equipment
        only = ["reference", "purchase"]

    reference = StringField(label="Référence :", validators=[DataRequired()])
    serial_number = StringField(label="Numéro de série :", validators=[DataRequired()])
    purchaseDate = DateField(
        label="Date d'achat :",
        format="%d/%m/%Y",
        default=datetime.now(),
        validators=[DataRequired()],
    )
    purchasePrice = FlexibleDecimalField(
        label="Prix d'achat :",
        validators=[DataRequired()],
        render_kw={"pattern": "^[0-9]+([.|,][0-9]+){0,1}$"},
    )
    equipment_model_id = SelectField(
        label="Modèle :", coerce=int, choices=[], validators=[DataRequired()]
    )
    # This field is used to let the form know that we didn't submit, we just changed the model
    update_model = HiddenField()
    # We can't this field 'submit', it'll block force submitting in js
    save_all = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.equipment_model_id.choices = [(-1, "")] + [
            (i.id, i.name) for i in EquipmentModel.query.all()
        ]


class DeleteForm(FlaskForm):
    """Form for deleting an equipment"""

    delete = SubmitField("Supprimer")
