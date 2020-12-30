"""Authentification related modules.

This module contains form related to authentification such as login
and account creation.
"""
from flask import Markup
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import InputRequired, EqualTo, DataRequired
from wtforms_alchemy import ModelForm
from wtforms_alchemy.utils import strip_string
from ..models import User, db
from .order import OrderedForm
from .validators import UniqueValidator, PasswordValidator, LicenseValidator


class LoginForm(FlaskForm):
    mail = StringField("Email", validators=[DataRequired()], filters=[strip_string])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    remember_me = BooleanField("Se souvenir de la connexion")
    submit = SubmitField("Login")


class AccountCreationForm(ModelForm, OrderedForm):
    class Meta:
        model = User
        only = ["mail", "license", "date_of_birth"]
        unique_validator = UniqueValidator
        strip_string_fields = True

    license = StringField(
        label="Numéro de licence",
        description=LicenseValidator().help_string(),
        render_kw={
            "placeholder": LicenseValidator().sample_value(),
            "pattern": LicenseValidator().pattern(),
        },
        validators=[
            LicenseValidator(),
            UniqueValidator(User.license, get_session=lambda: db.session),
        ],
    )

    field_order = ["mail", "license", "*"]

    submit = SubmitField("Activer le compte")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mail.description = "Utilisée lors de votre (ré-)inscription FFCAM"


class PasswordResetForm(FlaskForm):

    password = PasswordField(
        label="Choisissez un mot de passe",
        description=PasswordValidator().help_string(),
        validators=[InputRequired(), PasswordValidator()],
    )

    confirm = PasswordField(
        label="Confirmation du mot de passe",
        validators=[
            InputRequired(),
            EqualTo("password", message="Les mots de passe ne correspondent pas"),
        ],
    )

    submit = SubmitField("Activer le compte")


class LegalAcceptation(FlaskForm):
    legal_accepted = BooleanField(
        Markup(
            """
    Je reconnais avoir pris connaissance
    des effets du traitement des données à caractère personnel dont je
    fais l'objet et accepte que ce traitement soit effectué dans les
    limites des finalités portées à ma connaissance et conformément
    au RGPD.<br/>
    Si vous souhaitez plus d'informations à ce sujet, nous vous invitons
    à consulter la page consacrée en cliquant
    <a href="/legal">ICI</a>."""
        ),
        validators=[DataRequired()],
    )


class AccountActivationForm(PasswordResetForm, LegalAcceptation):
    pass


class AdminTokenCreationForm(FlaskForm):
    """Form for administrators to generate conformation tokens"""

    license = StringField(
        label="Numéro de licence",
        description=LicenseValidator().help_string(),
        render_kw={
            "placeholder": LicenseValidator().sample_value(),
            "pattern": LicenseValidator().pattern(),
        },
        validators=[
            DataRequired(),
            LicenseValidator(),
        ],
    )

    confirm = BooleanField("Confirmer la génération du jeton de confirmation")
    submit = SubmitField("Générer le jeton de confirmation")
