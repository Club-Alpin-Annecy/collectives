"""Module containing forms for updating user information
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import PasswordField, SubmitField
from wtforms import SelectField, BooleanField, HiddenField
from wtforms.validators import EqualTo
from wtforms_alchemy import ModelForm


from .order import OrderedModelForm
from ..models import User, photos, ActivityType, Role
from .validators import UniqueValidator, PasswordValidator


class AvatarForm:
    avatar_file = FileField(
        "Nouvelle photo de profil",
        validators=[FileAllowed(photos, "Image uniquement!")],
    )
    remove_avatar = BooleanField("Supprimer la photo de profil existante")

    def __init__(self, user):
        if not (user and user.avatar):
            del self.remove_avatar


class ConfirmPasswordForm:
    password = PasswordField(
        label="Nouveau mot de passe",
        description="Laisser vide pour conserver l'actuel",
        validators=[PasswordValidator()],
    )

    confirm = PasswordField(
        "Confirmation du nouveau mot de passe",
        validators=[
            EqualTo("password", message="Les mots de passe ne correspondent pas")
        ],
    )


class AdminTestUserForm(OrderedModelForm, AvatarForm, ConfirmPasswordForm):
    class Meta:
        model = User
        # Avatar is selected/modified by another field
        exclude = ["avatar", "license_expiry_date", "last_extranet_sync_time"]
        unique_validator = UniqueValidator

    submit = SubmitField("Enregistrer")

    field_order = [
        "enabled",
        "*",
        "avatar_file",
        "remove_avatar",
        "password",
        "confirm",
    ]

    def __init__(self, *args, **kwargs):
        OrderedModelForm.__init__(self, *args, **kwargs)
        AvatarForm.__init__(self, kwargs.get("obj"))


class AdminUserForm(OrderedModelForm, AvatarForm):
    class Meta:
        model = User
        # User should not be able to change a protected parameter
        only = ["enabled"]
        unique_validator = UniqueValidator

    submit = SubmitField("Enregistrer")
    field_order = ["enabled", "*", "avatar_file", "remove_avatar"]

    def __init__(self, *args, **kwargs):
        OrderedModelForm.__init__(self, *args, **kwargs)
        AvatarForm.__init__(self, kwargs.get("obj"))


class UserForm(OrderedModelForm, AvatarForm, ConfirmPasswordForm):
    class Meta:
        model = User
        # User should not be able to change a protected parameter
        only = ["password"]
        unique_validator = UniqueValidator

    submit = SubmitField("Enregistrer")
    field_order = ["*", "avatar_file", "remove_avatar", "password", "confirm"]

    def __init__(self, *args, **kwargs):
        OrderedModelForm.__init__(self, *args, **kwargs)
        AvatarForm.__init__(self, kwargs.get("obj"))


class RoleForm(ModelForm, FlaskForm):
    class Meta:
        model = Role

    activity_type_id = SelectField("Activité", choices=[])
    submit = SubmitField("Ajouter")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.activity_type_id.choices = [
            (a.id, a.name) for a in ActivityType.query.all()
        ]


class AddTraineeForm(FlaskForm):

    user_id = HiddenField()
    activity_type = SelectField("Activité", choices=[])
    submit = SubmitField("Ajouter un initiateur en formation")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        activity_list = current_user.get_supervised_activities()
        self.activity_type.choices = [
            (a.id, a.name) for a in activity_list
        ]
