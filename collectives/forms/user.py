"""Module containing forms for updating user information
"""

from datetime import date
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import PasswordField, SubmitField, StringField
from wtforms import SelectField, BooleanField, HiddenField, IntegerField
from wtforms.validators import EqualTo, DataRequired, Optional, ValidationError
from wtforms.fields import DateField
from wtforms_alchemy import ModelForm


from collectives.forms.order import OrderedModelForm
from collectives.forms.validators import UniqueValidator, PasswordValidator
from collectives.forms.validators import LicenseValidator

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


class ExtranetUserForm(OrderedModelForm, AvatarForm, ConfirmPasswordForm):
    """Form for extranet users to edit their own info"""

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


class LocalUserForm(OrderedModelForm, AvatarForm, ConfirmPasswordForm):
    """Form for extranet users to edit their own info"""

    class Meta:
        """Fields to expose"""

        model = User
        # User should not be able to change a protected parameter
        only = [
            "license",
            "date_of_birth",
            "phone",
            "emergency_contact_name",
            "emergency_contact_phone",
            "password",
        ]
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
            (a.id, a.name) for a in ActivityType.get_all_types(True) if not a.deprecated
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
        exclude = ["creation_time"]

    activity_type_id = SelectField("Activité", choices=[], coerce=int)
    submit = SubmitField("Ajouter")

    def __init__(self, *args, **kwargs):
        """Overloaded constructor populating activity list"""
        kwargs["expiration_date"] = compute_default_expiration_date()

        super().__init__(*args, **kwargs)

        # In case this is a CREATION
        self.activity_type_id.choices = [
            (a.id, a.name) for a in ActivityType.get_all_types(True)
        ]


class RenewBadgeForm(ModelForm, FlaskForm):
    """Form for administrators to add badges to users"""

    class Meta:
        """Fields to expose"""

        model = Badge
        exclude = ["creation_time"]

    activity_type_id = SelectField("Activité", choices=[], coerce=int)
    submit = SubmitField("Renouveler")

    def __init__(self, *args, **kwargs):
        """Overloaded constructor populating activity list"""
        badge = kwargs.pop("badge", {})
        kwargs["expiration_date"] = compute_default_expiration_date()
        if badge:
            if badge.level:
                kwargs["level"] = badge.level

        super().__init__(*args, **kwargs)
        # In case this is a RENEWAL
        if badge:
            if badge.activity_id:
                self.activity_type_id.choices = [
                    (badge.activity_id, ActivityType.get(badge.activity_id).name)
                ]
            if badge.badge_id:
                self.badge_id = [BadgeIds(int(badge.badge_id))]

        # In case this is a CREATION
        else:
            self.activity_type_id.choices = [
                (a.id, a.name) for a in ActivityType.get_all_types(True)
            ]


class AddLeaderForm(ActivityTypeSelectionForm):
    """Form for supervisors to add "Trainee" or "EventLeader" role to users"""

    user_id = HiddenField(id="user-search-resultid")
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
        kwargs["submit_label"] = "Ajouter un rôle"
        super().__init__(*args, **kwargs)


class AddBadgeForm(ActivityTypeSelectionForm):
    """Form for supervisors to add badges to Users"""

    user_id = HiddenField(id="user-search-resultid")
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
    expiration_date = DateField("Date d'expiration", format="%Y-%m-%d")
    level = IntegerField(
        "Niveau du badge",
        validators=[Optional()],
    )

    def __init__(self, *args, badge_type: str = "badge", **kwargs):
        """Overloaded constructor populating activity list.

        :param badge_type: The type of badge to be displayed in submit label"""

        if current_user.is_hotline():
            kwargs["activity_list"] = ActivityType.query.all()
        else:
            kwargs["activity_list"] = current_user.get_supervised_activities()

        kwargs["submit_label"] = f"Ajouter un {badge_type}"
        kwargs["expiration_date"] = compute_default_expiration_date()

        super().__init__(*args, **kwargs)


class DeleteUserForm(FlaskForm):
    """Form for confirming user suppression"""

    license = StringField(
        "Numéro de licence :",
        description=(
            "Pour confirmer la suppression, "
            "veuillez re-saisir le numéro de licence du compte."
        ),
        render_kw={
            "placeholder": "",
        },
    )

    submit = SubmitField("Supprimer le compte utilisateur")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._user = user
        self.license.render_kw["placeholder"] = LicenseValidator().sample_value()

    def validate_license(self, field: StringField):
        """Validates that the user confirmed the license number of the account to delete"""

        if field.data.strip() != self._user.license:
            raise ValidationError("Le numéro de license ne correspond pas")
