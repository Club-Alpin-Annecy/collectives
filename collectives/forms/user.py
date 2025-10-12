"""Module containing forms for updating user information"""

from datetime import date

from flask import request
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    HiddenField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.fields import DateField
from wtforms.validators import (
    DataRequired,
    EqualTo,
    InputRequired,
    Optional,
    ValidationError,
)
from wtforms_alchemy import ModelForm

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.forms.order import OrderedModelForm
from collectives.forms.validators import (
    LicenseValidator,
    PasswordValidator,
    UniqueValidator,
)
from collectives.forms.utils import coerce_optional
from collectives.models import (
    ActivityType,
    Badge,
    BadgeCustomLevel,
    BadgeIds,
    Role,
    RoleIds,
    User,
    photos,
)


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


class OptionalPasswordForm:
    """Form component adding password and password confirmation fields"""

    password = PasswordField(
        label="Nouveau mot de passe",
        description="Laisser vide pour conserver l'actuel",
        validators=[PasswordValidator()],
        render_kw={"passsword-reveal": "true"},
    )

    confirm = PasswordField(
        "Confirmation du nouveau mot de passe",
        validators=[
            EqualTo("password", message="Les mots de passe ne correspondent pas")
        ],
        render_kw={"passsword-reveal": "true"},
    )


class AdminTestUserForm(OrderedModelForm, AvatarForm, OptionalPasswordForm):
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
        only = ["enabled", "license_expiry_date"]
        unique_validator = UniqueValidator

    submit = SubmitField("Enregistrer")
    field_order = ["enabled", "*", "avatar_file", "remove_avatar"]

    def __init__(self, *args, **kwargs):
        OrderedModelForm.__init__(self, *args, **kwargs)
        AvatarForm.__init__(self, kwargs.get("obj"))


class ExtranetUserForm(OrderedModelForm, AvatarForm, OptionalPasswordForm):
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


class LocalUserForm(OrderedModelForm, AvatarForm, OptionalPasswordForm):
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


def compute_default_expiration_date(
    badge_id: BadgeIds | None = None, level: int | None = None
) -> date | None:
    """Compute the default expiration date for a badge"""
    # For now, the default expiration date is hard-coded.
    # It could be managable in the admin panel in a next version
    # NB: when we are after the default hard-coded date, but still in the same year,
    # then increment the year

    if badge_id and level in badge_id.levels():
        level_desc = badge_id.levels()[level]
        return level_desc.expiry_date()

    default_date = date(date.today().year, 9, 30)
    default_year = default_date.year
    if (date.today() >= default_date) and (date.today().year == default_year):
        default_date = date(date.today().year + 1, 9, 30)
    return default_date


class BadgeForm(ModelForm, ActivityTypeSelectionForm):
    """Form for administrators to add badges to users"""

    class Meta:
        """Fields to expose"""

        model = Badge
        exclude = ["creation_time"]

    submit = SubmitField("Ajouter")

    def __init__(self, *args, **kwargs):
        """Overloaded constructor populating activity list"""

        if "no_enabled" not in kwargs:
            kwargs["no_enabled"] = True

        super().__init__(*args, **kwargs)

        if "expiration_date" not in request.form:
            badge = kwargs.get("obj", None)
            if badge:
                self.expiration_date.data = compute_default_expiration_date(
                    badge.badge_id, badge.level
                )
            else:
                self.expiration_date.data = compute_default_expiration_date()

    def validate_level(self, field):
        """WTFForms validator function that make sure the level is consistent"""
        badge_id = BadgeIds(int(self.badge_id.data))
        levels = badge_id.levels()

        if not badge_id.requires_level():
            return

        level = int(field.data)
        if level not in levels:
            raise ValidationError("Niveau invalide")

        level_desc = levels[level]
        if not level_desc.is_compatible_with_activity(self.activity_id.data):
            raise ValidationError(
                f"Le choix '{level_desc.name}' est spécifique à l'activité '{level_desc.activity_name()}'"
            )


class RenewBadgeForm(BadgeForm):
    """Form for administrators to add badges to users"""

    class Meta:
        """Fields to expose"""

        model = Badge
        exclude = ["creation_time"]

    submit = SubmitField("Renouveler")

    def __init__(self, *args, badge: Badge, **kwargs):
        """Overloaded constructor populating activity list"""
        super().__init__(
            *args,
            obj=badge,
            **kwargs,
        )

        # In case this is a RENEWAL
        if badge.activity_id:
            self.activity_id.choices = [
                (badge.activity_id, ActivityType.get(badge.activity_id).name)
            ]
        self.badge_id.choices = [(int(badge.badge_id), str(badge.badge_id))]


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
        activity_list = current_user.get_supervised_activities()
        submit_label = "Ajouter un rôle"
        super().__init__(
            *args, activity_list=activity_list, submit_label=submit_label, **kwargs
        )


class AddBadgeForm(BadgeForm):
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

    def __init__(self, *args, badge_type: str = "badge", **kwargs):
        """Overloaded constructor populating activity list.

        :param badge_type: The type of badge to be displayed in submit label"""

        if current_user.is_hotline():
            activity_list = ActivityType.get_all_types()
            no_enabled = True
        else:
            activity_list = current_user.get_supervised_activities()
            no_enabled = False

        submit_label = f"Ajouter un {badge_type}"
        kwargs["expiration_date"] = compute_default_expiration_date()

        super().__init__(
            *args,
            activity_list=activity_list,
            no_enabled=no_enabled,
            submit_label=submit_label,
            **kwargs,
        )


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


class CompetencyBadgeForm(FlaskForm):
    """Form for administrators to add practitioner badges to users"""

    submit = SubmitField("Attribuer")

    level = SelectField(
        "Niveau",
        coerce=int,
        validators=[InputRequired()],
        choices=[],
    )

    activity_id = SelectField(
        "Activité",
        coerce=int,
        validators=[DataRequired()],
        choices=[],
    )

    def __init__(self, badge_id: BadgeIds, *args, **kwargs):
        """Overloaded constructor populating activity list"""

        super().__init__(*args, **kwargs)

        self.badge_id = badge_id
        self.submit.name = str(badge_id)

        led_activities = {
            a.id: a for a in current_user.get_organizable_activities(need_leader=True)
        }

        if badge_id == BadgeIds.Practitioner:
            self.level.choices = [(0, "Aucun")] + [
                (k, f"{desc.name} ({desc.abbrev})")
                for k, desc in badge_id.levels().items()
                if desc.activity_id is None or desc.activity_id in led_activities
            ]
            self.activity_id.choices = [
                (activity.id, activity.name) for activity in led_activities.values()
            ]
        else:
            self.level.choices = [
                (k, f"{desc.name} ({desc.activity_name()})")
                for k, desc in badge_id.levels().items()
                if desc.activity_id is None or desc.activity_id in led_activities
            ]
            del self.activity_id

    def empty(self) -> bool:
        """Returns True if the form has no selectable level"""
        return len(self.level.choices) == 0

    def validate_level(self, field):
        """WTFForms validator function that make sure the level field is not set
        if the selected badge has not meaningful levels"""
        badge_id = self.badge_id
        levels = badge_id.levels()

        if not field.data:
            field.data = None
            return

        level = int(field.data)
        if level not in levels:
            raise ValidationError("Niveau invalide")

        if self.activity_id is not None:
            level_desc = levels[level]
            if not level_desc.is_compatible_with_activity(self.activity_id.data):
                raise ValidationError(
                    f"Le choix '{level_desc.name}' est spécifique à l'activité '{level_desc.activity_name()}'"
                )


class BadgeCustomLevelForm(OrderedModelForm):
    """Form for activity supervisors to add or edit custom badge levels"""

    class Meta:
        """Fields to expose"""

        model = BadgeCustomLevel
        exclude = ["badge_id"]

    activity_id = SelectField("Activité", choices=[], coerce=coerce_optional(int))

    submit = SubmitField("Enregistrer")

    field_order = [
        "name",
        "abbrev",
        "activity_id",
        "*",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        supervised_activities = current_user.get_supervised_activities()
        self.activity_id.choices = [("", "N'importe quelle activité")] + [
            (activity.id, activity.name) for activity in supervised_activities
        ]
