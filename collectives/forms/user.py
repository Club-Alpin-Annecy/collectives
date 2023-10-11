"""Module containing forms for updating user information
"""
from datetime import date
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import PasswordField, SubmitField, StringField
from wtforms import SelectField, BooleanField, HiddenField, IntegerField
from wtforms.validators import EqualTo, DataRequired, Optional
from wtforms.fields import DateField
from wtforms_alchemy import ModelForm


from collectives.forms.order import OrderedModelForm
from collectives.forms.validators import UniqueValidator, PasswordValidator
from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.models import User, photos, ActivityType, Role, RoleIds
from collectives.models import Badge, BadgeIds


class AvatarForm:
    """Form component adding an avatar field"""

    avatar_file = FileField(
        "Nouvelle photo de profil",
        validators=[FileAllowed(photos, "Image uniquement!")],
    )
    remove_avatar = BooleanField("Supprimer la photo de profil existante")

    def __init__(self, user):
        if not (user and user.avatar):
            del self.remove_avatar


class ConfirmPasswordForm:
    """Form component adding password and password confirmation fields"""

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
    """Form for admins to edit test users info"""

    class Meta:
        """Fields to expose"""

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
    """Form for admins to edit real users info"""

    class Meta:
        """Fields to expose"""

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
    """Form for users to edit their own info"""

    class Meta:
        """Fields to expose"""

        model = User
        # User should not be able to change a protected parameter
        only = ["password"]
        unique_validator = UniqueValidator

    submit = SubmitField("Enregistrer")
    field_order = ["*", "avatar_file", "remove_avatar", "password", "confirm"]

    def __init__(self, *args, **kwargs):
        """Overloaded constructor"""
        OrderedModelForm.__init__(self, *args, **kwargs)
        AvatarForm.__init__(self, kwargs.get("obj"))


class RoleForm(ModelForm, FlaskForm):
    """Form for administrators to add roles to users"""

    class Meta:
        """Fields to expose"""

        model = Role

    activity_type_id = SelectField("Activité", choices=[], coerce=int)
    submit = SubmitField("Ajouter")

    def __init__(self, *args, **kwargs):
        """Overloaded constructor populating activity list"""
        super().__init__(*args, **kwargs)
        self.activity_type_id.choices = [
            (a.id, a.name) for a in ActivityType.get_all_types(True)
        ]


def compute_default_expiration_date():
    """Compute the default expiration date for a badge"""
    # For now, the default expiration date is hard-coded.
    # It could be managable in the admin panel in a next version
    # NB: when we are after the default hard-coded date, but still in the same year,
    # then increment the year
    default_date = date(date.today().year, 9, 30)
    default_year = default_date.year
    if (date.today() >= default_date) and (date.today().year == default_year):
        default_date = date(date.today().year + 1, 9, 30)
    return default_date


class BadgeForm(ModelForm, FlaskForm):
    """Form for administrators to add badges to users"""

    class Meta:
        """Fields to expose"""

        model = Badge

    activity_type_id = SelectField("Activité", choices=[], coerce=int)
    submit = SubmitField("Ajouter")

    def __init__(self, *args, **kwargs):
        """Overloaded constructor populating activity list"""
        initial = kwargs.pop("initial", {})
        kwargs["expiration_date"] = compute_default_expiration_date()
        if initial:
            if initial.level:
                kwargs["level"] = initial.level

        super().__init__(*args, **kwargs)
        # In case this is a RENEWAL
        if initial:
            if initial.activity_id:
                self.activity_type_id.choices = [
                    (initial.activity_id, ActivityType.get(initial.activity_id).name)
                ]
            if initial.badge_id:
                self.badge_id = [BadgeIds(int(initial.badge_id))]

        # In case this is a CREATION
        else:
            self.activity_type_id.choices = [
                (a.id, a.name) for a in ActivityType.get_all_types(True)
            ]


class AddLeaderForm(ActivityTypeSelectionForm):
    """Form for supervisors to add "Trainee" or "EventLeader" role to users"""

    user_id = HiddenField()
    user_search = StringField(
        "Utilisateur",
        render_kw={
            "autocomplete": "off",
            "class": "search-input",
            "placeholder": "Nom...",
        },
    )
    role_id = SelectField(
        "Rôle",
        coerce=int,
        validators=[DataRequired()],
        choices=[
            (int(r), r.display_name()) for r in RoleIds.all_supervisor_manageable()
        ],
    )

    def __init__(self, *args, **kwargs):
        """Overloaded constructor populating activity list"""
        kwargs["activity_list"] = current_user.get_supervised_activities()
        kwargs["submit_label"] = "Ajouter un encadrant"
        super().__init__(*args, **kwargs)


class AddBadgeForm(ActivityTypeSelectionForm):
    """Form for supervisors to add badges to Users"""

    user_id = HiddenField()
    user_search = StringField(
        "Utilisateur",
        render_kw={
            "autocomplete": "off",
            "class": "search-input",
            "placeholder": "Nom...",
        },
    )
    badge_id = SelectField(
        "Badge",
        coerce=int,
        validators=[DataRequired()],
        choices=BadgeIds.choices(),
    )
    expiration_date = DateField("Expiration Date", format="%Y-%m-%d")
    level = IntegerField(
        "Niveau du badge",
        validators=[Optional()],
    )

    def __init__(self, *args, **kwargs):
        """Overloaded constructor populating activity list"""
        kwargs["activity_list"] = current_user.get_supervised_activities()
        kwargs["submit_label"] = "Ajouter un badge"
        kwargs["expiration_date"] = compute_default_expiration_date()

        super().__init__(*args, **kwargs)
