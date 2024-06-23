"""Authentification related modules.

This module contains form related to authentification such as login
and account creation.
"""

from markupsafe import Markup
from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import InputRequired, EqualTo, DataRequired
from wtforms_alchemy import ModelForm
from wtforms_alchemy.utils import strip_string

from collectives.forms.order import OrderedForm
from collectives.forms.validators import UniqueValidator, PasswordValidator
from collectives.forms.validators import remove_unique_validators
from collectives.models import User, Configuration
from collectives.forms.utils import LicenseField, PhoneField


class LoginForm(FlaskForm):
    """Form to log a user ."""

    mail = StringField("Email", validators=[DataRequired()], filters=[strip_string])
    password = PasswordField("Mot de passe", validators=[DataRequired()])
    remember_me = BooleanField("Se souvenir de la connexion")
    submit = SubmitField("Login")


class ExtranetAccountCreationForm(ModelForm, OrderedForm):
    """Form to create an account from extranet"""

    class Meta:
        """Fields to expose"""

        model = User
        only = ["mail", "license", "date_of_birth"]
        unique_validator = UniqueValidator
        strip_string_fields = True

    license = LicenseField()

    field_order = ["mail", "license", "*"]

    submit = SubmitField("Activer le compte")

    def __init__(self, is_recover, *args, **kwargs):
        """Constructor to specialize the form regarding if it is a creation or a recover.

        :param bool is_recover: True if form is for a password recover, False for a creation
        """
        super().__init__(*args, **kwargs)

        if is_recover:
            self.license.validators = remove_unique_validators(self.license.validators)
            self.mail.validators = remove_unique_validators(self.mail.validators)

        self.mail.description = "Utilisée lors de votre (ré-)inscription FFCAM"


class PasswordForm(FlaskForm):
    """Form with a field to give change password"""

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


class PasswordResetForm(PasswordForm):
    """Form for a user to set or reset his password."""

    submit = SubmitField("Activer le compte")


class LegalAcceptation(FlaskForm):
    """Form to accept or reject the legal terms of the site"""

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
    """Final form merging password (re)set and legal acceptance."""

    pass


class AdminTokenCreationForm(FlaskForm):
    """Form for administrators to generate conformation tokens"""

    license = LicenseField()
    confirm = BooleanField("Confirmer la génération du jeton de confirmation")
    submit = SubmitField("Générer le jeton de confirmation")


class LocalAccountCreationForm(PasswordForm, ModelForm, OrderedForm, LegalAcceptation):
    """Form to create an account from extranet"""

    class Meta:
        """Fields to expose"""

        model = User
        only = [
            "mail",
            "first_name",
            "last_name",
            "phone",
            "emergency_contact_name",
            "emergency_contact_phone",
            "gender",
            "license",
            "date_of_birth",
            "password",
        ]
        unique_validator = UniqueValidator
        strip_string_fields = True

    license = LicenseField()
    phone = PhoneField(label=User.phone.info["label"])
    emergency_contact_phone = PhoneField(
        label=User.emergency_contact_phone.info["label"]
    )

    field_order = [
        "mail",
        "first_name",
        "last_name",
        "gender",
        "phone",
        "emergency_contact_name",
        "emergency_contact_phone",
        "license",
        "date_of_birth",
        "password",
        "confirm",
        "legal_accepted",
        "recaptcha",
    ]

    recaptcha = RecaptchaField()

    submit = SubmitField("Créer le compte")

    def __init__(self, *args, **kwargs):
        """Constructor to specialize the form regarding if it is a creation or a recover.

        :param bool is_recover: True if form is for a password recover, False for a creation
        """
        super().__init__(*args, **kwargs)

        self.mail.description = "Utilisée lors de votre (ré-)inscription FFCAM"
        self.emergency_contact_name.description = (
            "Personne a contacter en cas d'accident."
        )
        self.mail.description = "Utilisée lors de votre (ré-)inscription FFCAM"

        if Configuration.RECAPTCHA_PUBLIC_KEY == "":
            del self.recaptcha
