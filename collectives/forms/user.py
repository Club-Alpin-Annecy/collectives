from .order import OrderedForm, OrderedModelForm
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import PasswordField, SubmitField
from wtforms import SelectField, BooleanField
from wtforms.validators import EqualTo
from wtforms_alchemy import ModelForm, Unique


from ..models import User, photos, ActivityType, Role, RoleIds
from .validators import UniqueValidator, PasswordValidator


class AvatarForm():
    avatar_file = FileField("Nouvel avatar",
                            validators=[FileAllowed(photos, 'Image uniquement!')])
    remove_avatar = BooleanField("Supprimer l'avatar existant")

    def __init__(self, user):
        if not (user and user.avatar):
            del self.remove_avatar


class ConfirmPasswordForm():
    password = PasswordField(
        label='Nouveau mot de passe',
        description='Laisser vide pour conserver l\'actuel',
        validators=[PasswordValidator()])

    confirm = PasswordField(
        'Confirmation du nouveau mot de passe',
        validators=[EqualTo('password',
                            message='Les mots de passe ne correspondent pas')])


class AdminTestUserForm(OrderedModelForm, AvatarForm, ConfirmPasswordForm):
    class Meta:
        model = User
        # Avatar is selected/modified by another field
        exclude = ['avatar', 'license_expiry_date', 'last_extranet_sync_time']
        unique_validator = UniqueValidator

    submit = SubmitField('Enregistrer')

    field_order = ['enabled', '*', 'avatar_file',
                   'remove_avatar', 'password', 'confirm']

    def __init__(self, *args, **kwargs):
        OrderedModelForm.__init__(self, *args, **kwargs)
        AvatarForm.__init__(self, kwargs.get('obj'))


class AdminUserForm(OrderedModelForm, AvatarForm):
    class Meta:
        model = User
        # User should not be able to change a protected parameter
        only = ['enabled']
        unique_validator = UniqueValidator

    submit = SubmitField('Enregistrer')
    field_order = ['enabled', '*', 'avatar_file', 'remove_avatar']

    def __init__(self, *args, **kwargs):
        OrderedModelForm.__init__(self, *args, **kwargs)
        AvatarForm.__init__(self, kwargs.get('obj'))


class UserForm(OrderedModelForm, AvatarForm, ConfirmPasswordForm):
    class Meta:
        model = User
        # User should not be able to change a protected parameter
        only = ['password']
        unique_validator = UniqueValidator

    submit = SubmitField('Enregistrer')
    field_order = ['*', 'avatar_file', 'remove_avatar', 'password', 'confirm']

    def __init__(self, *args, **kwargs):
        OrderedModelForm.__init__(self, *args, **kwargs)
        AvatarForm.__init__(self, kwargs.get('obj'))


class RoleForm(ModelForm, FlaskForm):
    class Meta:
        model = Role

    activity_type_id = SelectField('Activité', choices=[])
    submit = SubmitField('Ajouter')

    def __init__(self, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        self.activity_type_id.choices = [(a.id, a.name
                                          ) for a in ActivityType.query.all()]
