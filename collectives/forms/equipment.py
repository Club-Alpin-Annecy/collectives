"""Equipment related modules.

This module contains form related to equipment.
"""
from flask import Markup
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms.validators import InputRequired, EqualTo, DataRequired
from wtforms_alchemy import ModelForm, QuerySelectField
from wtforms_alchemy.utils import strip_string
from ..models import Equipment, EquipmentType, EquipmentModel, db
from .order import OrderedForm
from .validators import UniqueValidator, PasswordValidator, LicenseValidator
from .validators import remove_unique_validators



class AddEquipmentTypeForm(FlaskForm):
    class Meta:
        model = EquipmentType
        only = ["type_name"]
        
    libelleEquipmentType = StringField("Type d'équipement :")
    priceEquipmentType = StringField("Prix :")
    submit = SubmitField("Enregistrer")

class AddEquipmentModelForm(FlaskForm):
    class Meta:
        model = EquipmentModel
        only = ["name", "equipmentType"]
        
    name = StringField("Type d'équipement :")

    equipmentType = QuerySelectField(
        query_factory=lambda: EquipmentType.query.all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
    )
    submit = SubmitField("Enregistrer")

class DeleteEquipmentForm(FlaskForm):
    # equipment_id = HiddenField()
    delete = SubmitField("Supprimer")


