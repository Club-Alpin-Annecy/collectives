from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms import SelectField, IntegerField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_wtf.csrf import CSRFProtect
from wtforms.validators import Email, InputRequired, EqualTo
from flask_uploads import UploadSet, configure_uploads, patch_request_class
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelForm
from flask import current_app
import sys

from .models import Event, User, photos, avatars, ActivityType, Role, RoleIds
from .models import Registration, EventStatus

csrf = CSRFProtect()


def configure_forms(app):
    configure_uploads(app, photos)
    configure_uploads(app, avatars)

    # set maximum file size, default is 3MB
    patch_request_class(app, 3 * 1024 * 1024)


class LoginForm(FlaskForm):
    mail = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de la connexion')
    submit = SubmitField('Login')


class EventForm(ModelForm, FlaskForm):
    class Meta:
        model = Event
        exclude = ['photo']
    photo_file = FileField(validators=[FileAllowed(photos, 'Image only!')])
    duplicate_photo = HiddenField()
    type = SelectField('Type', choices=[])
    status = SelectField('État', choices=[])

    def __init__(self, activity_choices, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.type.choices = activity_choices
        self.status.choices = [(s.value, s.display_name()) for s in EventStatus]


class AdminUserForm(ModelForm, FlaskForm):
    class Meta:
        model = User
        # Avatar is selected/modified by another field
        exclude = ['avatar', 'license_expiry_date', 'last_extranet_sync_time']
        # FIXME Administrator should not be able to change a password,
        #exclude = ['password']

    password = PasswordField(
        'Nouveau mot de passe',
        [EqualTo('confirm',
                 message='Les mots de passe ne correspondent pas')])
    confirm = PasswordField('Confirmation du mot de passe')

    validators = {'mail': [Email()]}
    submit = SubmitField('Enregistrer')
    avatar_file = FileField(validators=[FileAllowed(photos, 'Image only!')])


class UserForm(ModelForm, FlaskForm):
    class Meta:
        model = User
        # User should not be able to change a protected parameter
        exclude = User.protected

    password = PasswordField(
        'Nouveau mot de passe',
        [EqualTo('confirm',
                 message='Les mots de passe ne correspondent pas')])
    confirm = PasswordField('Confirmation du mot de passe')

    avatar = FileField(validators=[FileAllowed(photos, 'Image only!')])
    validators = {'mail': [Email()]}
    submit = SubmitField('Enregistrer')


class AccountCreationForm(ModelForm, FlaskForm):
    class Meta:
        model = User
        only = ['mail', 'license', 'date_of_birth']

    password = PasswordField(
        'Nouveau mot de passe',
        [InputRequired(),
         EqualTo('confirm',
                 message='Les mots de passe ne correspondent pas')])
    confirm = PasswordField('Confirmation du mot de passe')

    validators = {'mail': [Email()]}
    submit = SubmitField('Activer le compte')


class RoleForm(ModelForm, FlaskForm):
    class Meta:
        model = Role

    role_id = SelectField('Role', choices=[])
    activity_type_id = SelectField('Activité', choices=[])
    submit = SubmitField('Ajouter')

    def __init__(self, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        self.activity_type_id.choices = [(a.id, a.name
                                          ) for a in ActivityType.query.all()]
        self.role_id.choices = [(r.value, r.display_name()) for r in RoleIds]


class RegistrationForm(ModelForm, FlaskForm):
    class Meta:
        model = Registration
        exclude = ['status', 'level']

    user_id = IntegerField('Id')
    submit = SubmitField('Inscrire')

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
