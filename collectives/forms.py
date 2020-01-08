from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms import SelectField, IntegerField, HiddenField, TextAreaField
from wtforms.validators import Email, InputRequired, EqualTo, ValidationError
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelForm, Unique
from flask_uploads import UploadSet, configure_uploads, patch_request_class
from flask import current_app
from collections import OrderedDict
import sys
import re

from .models import Event, User, photos, avatars, ActivityType, Role, RoleIds
from .models import Registration, EventStatus

csrf = CSRFProtect()


def configure_forms(app):
    configure_uploads(app, photos)
    configure_uploads(app, avatars)

    # set maximum file size, default is 3MB
    patch_request_class(app, 3 * 1024 * 1024)


class LicenseValidator:
    prefix = '7400'
    length = 12

    def __call__(self, form, field):
        val = field.data
        if not (len(val) == self.length and val.isdigit() and
                val.startswith(self.prefix)):
            raise ValidationError(
                ("Le numéro de licence doit contenir 12 chiffres " +
                 "et commecer par '{}'".format(self.prefix)))

    def help_string(self):
        return '{len} chiffres commencant par \'{pref}\''.format(
            len=self.length, pref=self.prefix)

    def sample_value(self):
        return self.prefix + 'X' * (self.length - len(self.prefix))


class PasswordValidator:
    min_length = 8
    min_classes = 3

    def __call__(self, form, field):
        password = field.data

        # Allow empty password, if it is requied another InputRequired()
        # validator will be used
        if password == '':
            return

        if len(password) < self.min_length:
            raise ValidationError("Le mot de passe doit contenir au moins " +
                                  "{} caractères".format(self.min_length))

        num_classes = 0
        if re.search(r"\d", password):
            num_classes += 1
        if re.search(r"[A-Z]", password):
            num_classes += 1
        if re.search(r"[a-z]", password):
            num_classes += 1
        if re.search(r"[ !@;:%#$%&'()*+,-./[\\\]^_`{|}<>~+=?`]", password):
            num_classes += 1

        if num_classes < self.min_classes:
            raise ValidationError(
                ("Le mot de passe doit contenir au moins " +
                 "{} classes de caractères".format(self.min_classes) +
                 " parmi majuscules, minuscules, chiffres et " +
                 " caractères spéciaux"))

    def help_string(self):
        return ('Au moins {len} caractères dont majuscules, minuscules,'
                + ' chiffres ou caractère spéciaux').format(
            len=self.min_length)


class UniqueValidator(Unique):
    def __init__(self, column=None, get_session=None, message='déjà associée à un compte'):
        Unique.__init__(self, column=column,
                        get_session=get_session, message=message)


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
        unique_validator = UniqueValidator

    confirm = PasswordField(
        'Confirmation du nouveau mot de passe',
        validators=[EqualTo('password',
                            message='Les mots de passe ne correspondent pas')])

    submit = SubmitField('Enregistrer')
    avatar_file = FileField(validators=[FileAllowed(photos, 'Image only!')])
    field_order = ['*', 'avatar_file', 'password', 'confirm']


class UserForm(ModelForm, OrderedForm):
    class Meta:
        model = User
        # User should not be able to change a protected parameter
        only = User.mutable
        unique_validator = UniqueValidator

    password = PasswordField(
        label='Nouveau mot de passe',
        description='Laisser vide pour conserver l\'actuel',
        validators=[PasswordValidator()])

    confirm = PasswordField(
        'Confirmation du nouveau mot de passe',
        validators=[EqualTo('password',
                            message='Les mots de passe ne correspondent pas')])

    avatar = FileField(validators=[FileAllowed(photos, 'Image only!')])
    submit = SubmitField('Enregistrer')
    field_order = ['*', 'avatar', 'password', 'confirm']

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)


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


class CSVForm(FlaskForm):
    csv_file = FileField("Fichier Csv", validators=[InputRequired()])
    description = TextAreaField('Template de description')
    submit = SubmitField('Import')
    type = SelectField('Type d\'activité', choices=[])

    def __init__(self, activity_choices, *args, **kwargs):
        super(CSVForm, self).__init__(*args, **kwargs)
        self.type.choices = activity_choices
