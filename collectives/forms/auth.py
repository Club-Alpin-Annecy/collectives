from .order import OrderedForm
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import Email, InputRequired, EqualTo, DataRequired
from wtforms_alchemy import ModelForm, Unique


from ..models import User
from .validators import UniqueValidator, PasswordValidator, LicenseValidator


class LoginForm(FlaskForm):
    mail = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de la connexion')
    submit = SubmitField('Login')


class AccountCreationForm(ModelForm, OrderedForm):
    class Meta:
        model = User
        only = ['mail', 'license', 'date_of_birth', 'password']
        unique_validator = UniqueValidator

    password = PasswordField(
        label='Choisissez un mot de passe',
        description=PasswordValidator().help_string(),
        validators=[InputRequired(), PasswordValidator()])

    confirm = PasswordField(
        label='Confirmation du mot de passe',
        validators=[InputRequired(),
                    EqualTo('password',
                            message='Les mots de passe ne correspondent pas')])

    license = StringField(
        label='Numéro de licence',
        description=LicenseValidator().help_string(),
        render_kw={'placeholder': LicenseValidator().sample_value()},
        validators=[LicenseValidator()])

    field_order = ['mail', 'license', '*', 'password', 'confirm']

    submit = SubmitField('Activer le compte')

    def __init__(self, *args, **kwargs):
        super(AccountCreationForm, self).__init__(*args, **kwargs)
        self.mail.description = "Utilisée lors de votre inscription au club"
