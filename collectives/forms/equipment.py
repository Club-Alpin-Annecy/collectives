"""Equipment related modules.

This module contains form related to equipment.
"""
from flask import Markup
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField, DateField, DecimalField,FloatField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import InputRequired, EqualTo, DataRequired
from wtforms_alchemy import ModelForm, QuerySelectField
from wtforms_alchemy.utils import strip_string
from ..models import Equipment, EquipmentType, EquipmentModel, db,photos
from .order import OrderedForm
from .validators import UniqueValidator, PasswordValidator, LicenseValidator
from .validators import remove_unique_validators



class AddEquipmentTypeForm(FlaskForm):
    class Meta:
        model = EquipmentType
        only = ["type_name"]
        
    name = StringField(label="Type d'équipement :", validators=[DataRequired()])
    price = FloatField(label="Prix :",render_kw={"pattern": "^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)$","placeholder":"Prix"})
    imageType_file = FileField("Ajouter une image :",validators=[FileAllowed(photos, "Image uniquement!")])
    submit = SubmitField("Enregistrer")

class EquipmentModelForm(FlaskForm):
    class Meta:
        model = EquipmentModel
        only = ["name", "equipmentType"]
        
    name = StringField("Model d'équipement :")

    equipmentType = QuerySelectField("Type d'équipement : ",
        query_factory=lambda: EquipmentType.query.all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name,
        allow_blank=False,
    )
    submit = SubmitField("Enregistrer")

class EquipmentForm(FlaskForm):
    class Meta:
        model = Equipment
        only = ["reference", "purchase"]
        
    reference = StringField("Référence de l'équipement :")

    purchaseDate = DateField("Date d'achat :",format='%d/%m/%Y')

    purchasePrice = DecimalField("Prix d'achat :")

    model = QuerySelectField( "Model :",
        query_factory=lambda: EquipmentModel.query.all(),
        get_pk=lambda a: a.id,
        get_label=lambda a: a.name + "   ("+a.equipmentType.name+")",
        allow_blank=True,
    )
    submit = SubmitField("Enregistrer")


class DeleteForm(FlaskForm):
    
    delete = SubmitField("Supprimer")

