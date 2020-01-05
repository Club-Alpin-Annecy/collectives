from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms import SelectField, IntegerField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_wtf.csrf import CSRFProtect
from wtforms.validators import Email, InputRequired, EqualTo, Length, ValidationError
from flask_uploads import UploadSet, configure_uploads, patch_request_class
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelForm
from flask import current_app
from collections import OrderedDict
import sys

from .models import Event, User, photos, avatars, ActivityType, Role, RoleIds
from .models import Registration, EventStatus

csrf = CSRFProtect()


def configure_forms(app):
    configure_uploads(app, photos)
    configure_uploads(app, avatars)

    # set maximum file size, default is 3MB
    patch_request_class(app, 3 * 1024 * 1024)


class OrderedForm(FlaskForm):
    """
    Extends FlaskForm with an optional 'field_order' property
    """

    def __iter__(self):
        field_order = getattr(self, 'field_order', None)
        if field_order:
            fields = self._fields
            temp_fields = OrderedDict()
            for name in field_order:
                if name == '*':
                    temp_fields.update(
                        {n: f for n, f in fields.items() if n not in field_order})
                else:
                    temp_fields[name] = fields[name]
            self._fields = temp_fields
        return super(OrderedForm, self).__iter__()


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
        self.status.choices = [(s.value, s.display_name())
                               for s in EventStatus]


class AdminUserForm(ModelForm, OrderedForm):
    class Meta:
        model = User
        # Avatar is selected/modified by another field
        exclude = ['avatar', 'license_expiry_date', 'last_extranet_sync_time']
        # FIXME Administrator should not be able to change a password,
        # exclude = ['password']

    confirm = PasswordField(
        'Confirmation du mot de passe',
        [EqualTo('password',
                 message='Les mots de passe ne correspondent pas')])

    submit = SubmitField('Enregistrer')
    avatar_file = FileField(validators=[FileAllowed(photos, 'Image only!')])
    field_order = ['*', 'avatar_file', 'password', 'confirm']


class UserForm(ModelForm, OrderedForm):
    class Meta:
        model = User
        # User should not be able to change a protected parameter
        exclude = User.protected

    confirm = PasswordField(
        'Confirmation du mot de passe',
        [EqualTo('password',
                 message='Les mots de passe ne correspondent pas')])

    avatar = FileField(validators=[FileAllowed(photos, 'Image only!')])
    submit = SubmitField('Enregistrer')
    field_order = ['*', 'avatar', 'password', 'confirm']


def check_license_format(form, field):
    value = field.data
    if not (len(value) == 12 and value.isdigit() and value.startswith('7400')):
        raise ValidationError("Le numéro de licence doit contenir " +
                              "12 chiffres et commencer par '7400'")


class AccountCreationForm(ModelForm, OrderedForm):
    class Meta:
        model = User
        only = ['mail', 'license', 'date_of_birth', 'password']

    confirm = PasswordField(
        'Confirmation du mot de passe',
        [InputRequired(),
         EqualTo('password',
                 message='Les mots de passe ne correspondent pas')])

    license = StringField(
        label='Numéro de license',
        description='12 chiffres commencant par \'7400\'',
        render_kw={'placeholder': '7400YYYYXXXX'},
        validators=[check_license_format])

    field_order = ['mail', 'license', '*', 'password', 'confirm']

    submit = SubmitField('Activer le compte')

    def __init__(self, *args, **kwargs):
        super(AccountCreationForm, self).__init__(*args, **kwargs)
        self.mail.description = "Utilisée lors de votre inscription au club"


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
