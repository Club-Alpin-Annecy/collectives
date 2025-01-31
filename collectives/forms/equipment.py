"""Module containing forms related to equipment management"""

from datetime import datetime
from decimal import Decimal

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed

from wtforms import StringField, SubmitField, DateField, SelectField, HiddenField
from wtforms import DecimalField
from wtforms.validators import DataRequired, NumberRange
from wtforms_alchemy import ModelForm

from collectives.forms.validators import UniqueValidator
from collectives.models import Equipment, EquipmentType, EquipmentModel, photos, db


class LocalizedDecimalField(DecimalField):
    """
    DecimalField with french locale
    """

    def __init__(
        self,
        *args,
        min_value: float = 0,
        max_value: float = 10000,
        placeholder: str = "",
        **kwargs
    ):
        super().__init__(
            validators=[
                NumberRange(
                    min=min_value,
                    max=max_value,
                    message="Le prix doit être compris entre %(min)s et %(max)s euros.",
                )
            ],
            number_format="#,##0.00",
            render_kw={
                "type": "number",
                "min": min_value,
                "max": max_value,
                "placeholder": placeholder,
                "step": "0.01",
                "lang": "fr-FR",
            },
            default=Decimal(0),
            *args,
            **kwargs
        )


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
    price = LocalizedDecimalField(placeholder="Prix", label="Prix :")
    deposit = LocalizedDecimalField(label="Caution :", placeholder="Caution")
    imageType_file = FileField(
        "Ajouter une image :", validators=[FileAllowed(photos, "Image uniquement!")]
    )
    submit = SubmitField("Enregistrer")


class EquipmentModelForm(FlaskForm, ModelForm):
    """Form for adding an equipment model, specifying its name and type"""

    class Meta:
        """Fields to expose"""

        model = EquipmentModel
        only = ["name", "equipment_type_id", "manufacturer"]

    submit = SubmitField("Enregistrer")


class EquipmentForm(FlaskForm):
    """Form for adding an equipment, specifying its reference, model, purchase date and price"""

    class Meta:
        """Fields to expose"""

        model = Equipment
        only = ["reference", "purchase"]

    reference = StringField(label="Référence :", validators=[DataRequired()])
    serial_number = StringField(label="Numéro de série :", validators=[DataRequired()])
    purchase_date = DateField(
        label="Date d'achat :",
        default=datetime.now(),
        validators=[DataRequired()],
    )
    purchase_price = LocalizedDecimalField(label="Prix d'achat :")
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
