"""Authentification related modules.

This module contains form related to authentification such as login
and account creation.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import InputRequired, EqualTo, DataRequired
from wtforms_alchemy import ModelForm

from ..models import User
from .order import OrderedForm
from .validators import UniqueValidator, PasswordValidator, LicenseValidator


class LoginForm(FlaskForm):
    mail = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    remember_me = BooleanField("Se souvenir de la connexion")
    submit = SubmitField("Login")


class AccountCreationForm(ModelForm, OrderedForm):
    class Meta:
        model = User
        only = ["mail", "license", "date_of_birth"]
        unique_validator = UniqueValidator

    license = StringField(
        label="Numéro de licence",
        description=LicenseValidator().help_string(),
        render_kw={"placeholder": LicenseValidator().sample_value()},
        validators=[LicenseValidator()],
    )

    field_order = ["mail", "license", "*"]

    submit = SubmitField("Activer le compte")

    def __init__(self, *args, **kwargs):
        super(AccountCreationForm, self).__init__(*args, **kwargs)
        self.mail.description = "Utilisée lors de votre inscription au club"


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
        """Je reconnais avoir pris connaissance
    des effets du traitement des données à caractère personnel dont je
    fais l'objet et accepte que ce traitement soit effectué dans les
    limites des finalités portées à ma connaissance et conformément
    au RGPD.<br/>
    Si vous souhaitez plus d'informations à ce sujet, nous vous invitons
    à consulter la page consacrée en cliquant
    <a href="/legal">ICI</a>. """,
        validators=[DataRequired()],
    )


class AccountActivationForm(PasswordResetForm, LegalAcceptation):
    pass
