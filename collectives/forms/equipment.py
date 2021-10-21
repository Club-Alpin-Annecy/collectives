"""Equipment related modules.

This module contains form related to equipment.
"""
from flask import Markup
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField,FloatField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import InputRequired, EqualTo, DataRequired
from wtforms_alchemy import ModelForm
from wtforms_alchemy.utils import strip_string
from ..models import Equipment, EquipmentType, EquipmentModel, db,photos
from .order import OrderedForm
from .validators import UniqueValidator, PasswordValidator, LicenseValidator
from .validators import remove_unique_validators



class AddEquipmentTypeForm(FlaskForm):
    class Meta:
        model = EquipmentType
        only = ["type_name"]
        
    libelleEquipmentType = StringField(label="Type d'équipement :", validators=[DataRequired()])
    priceEquipmentType = FloatField(label="Prix :",render_kw={"pattern": "^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)$","placeholder":"Prix"})
    imageType_file = FileField("Ajouter image",validators=[FileAllowed(photos, "Image uniquement!")])
    submit = SubmitField("Enregistrer")


