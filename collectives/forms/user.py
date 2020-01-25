from .order import OrderedForm
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import PasswordField, SubmitField
from wtforms import SelectField
from wtforms.validators import EqualTo
from wtforms_alchemy import ModelForm, Unique


from ..models import User, photos, ActivityType, Role, RoleIds
from .validators import UniqueValidator, PasswordValidator


class AvatarForm():
    avatar = FileField(validators=[FileAllowed(photos, 'Image uniquement!')])

class ConfirmPasswordForm():
    password = PasswordField(
        label='Nouveau mot de passe',
        description='Laisser vide pour conserver l\'actuel',
        validators=[PasswordValidator()])

    confirm = PasswordField(
        'Confirmation du nouveau mot de passe',
        validators=[EqualTo('password',
                            message='Les mots de passe ne correspondent pas')])


class AdminTestUserForm(ModelForm, OrderedForm, AvatarForm, ConfirmPasswordForm):
    class Meta:
        model = User
        # Avatar is selected/modified by another field
        exclude = ['avatar', 'license_expiry_date', 'last_extranet_sync_time']
        # FIXME Administrator should not be able to change a password,
        # exclude = ['password']
        unique_validator = UniqueValidator

    submit = SubmitField('Enregistrer')

    field_order = ['*', 'avatar', 'password', 'confirm']


class AdminUserForm(ModelForm, OrderedForm, AvatarForm, ConfirmPasswordForm):
    class Meta:
        model = User
        # User should not be able to change a protected parameter
        only = ['password', 'enabled']
        unique_validator = UniqueValidator

    submit = SubmitField('Enregistrer')
    field_order = ['*', 'avatar', 'password', 'confirm']


class UserForm(ModelForm, OrderedForm, AvatarForm, ConfirmPasswordForm):
    class Meta:
        model = User
        # User should not be able to change a protected parameter
        only = ['password']
        unique_validator = UniqueValidator

    submit = SubmitField('Enregistrer')
    field_order = ['*', 'avatar', 'password', 'confirm']




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
