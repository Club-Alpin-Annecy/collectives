"""Module containing forms for updating user information"""

from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    EqualTo,
    ValidationError,
)
from wtforms_alchemy import ModelForm

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.forms.order import OrderedModelForm
from collectives.forms.utils import MultiCheckboxField, coerce_optional
from collectives.forms.validators import (
    LicenseValidator,
    PasswordValidator,
    UniqueValidator,
)
from collectives.models import (
    ActivityKind,
    ActivityType,
    EventType,
    NotificationFrequency,
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


class AdminTestUserCreationForm(AdminTestUserForm):
    """Form for admins to create test/local users without notification internals."""

    class Meta(AdminTestUserForm.Meta):
        """Fields to expose on creation."""

        exclude = AdminTestUserForm.Meta.exclude + [
            "new_event_notification_enabled",
            "new_event_notification_weekdays",
            "new_event_notification_frequency",
            "last_new_event_notification_sent_at",
            "last_new_event_notification_clicked_at",
            "new_event_notification_warning_sent_at",
        ]


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


class NotificationPreferencesForm(FlaskForm):
    """Form for managing event creation notification preferences."""

    WEEKDAY_CHOICES = [
        (0, "Lundi"),
        (1, "Mardi"),
        (2, "Mercredi"),
        (3, "Jeudi"),
        (4, "Vendredi"),
        (5, "Samedi"),
        (6, "Dimanche"),
    ]

    new_event_notification_enabled = BooleanField(
        "Recevoir des notifications de nouvelles collectives",
        description=(
            "Si activé, vous recevrez un e-mail groupé quand des collectives "
            "correspondent aux filtres ci-dessous."
        ),
    )
    new_event_notification_frequency = SelectField(
        "Fréquence d'envoi",
        coerce=NotificationFrequency.coerce,
        choices=NotificationFrequency.choices(),
        description="Choisissez un récapitulatif quotidien ou hebdomadaire.",
    )
    event_type_ids = MultiCheckboxField(
        "Types d'événement",
        coerce=int,
        description="Laisser vide pour tous les types.",
    )
    activity_type_ids = MultiCheckboxField(
        "Activités",
        coerce=int,
        description="Laisser vide pour toutes les activités.",
    )
    weekdays = MultiCheckboxField(
        "Jours de la semaine",
        choices=WEEKDAY_CHOICES,
        coerce=int,
        description="Laisser vide pour tous les jours.",
    )
    next = HiddenField()
    submit = SubmitField("Enregistrer")

    def __init__(self, user: User, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

        event_types = EventType.get_all_types()
        activity_types = ActivityType.get_all_types()
        self.event_type_requires_activity_ids = {
            event_type.id for event_type in event_types if event_type.requires_activity
        }
        self.event_type_icon_names = {
            event_type.id: event_type.short for event_type in event_types
        }
        self.event_type_ids.choices = [
            (event_type.id, event_type.name) for event_type in event_types
        ]
        self.activity_type_icon_names = {
            activity_type.id: (
                activity_type.short
                if activity_type.kind == ActivityKind.Regular
                else "benevolat"
            )
            for activity_type in activity_types
        }
        self.activity_type_ids.choices = [
            (activity_type.id, activity_type.name) for activity_type in activity_types
        ]

        if not self.is_submitted():
            self.new_event_notification_enabled.data = (
                user.new_event_notification_enabled
            )
            self.new_event_notification_frequency.data = (
                user.new_event_notification_frequency
            )
            self.event_type_ids.data = [
                event_type.id for event_type in user.notified_event_types
            ]
            self.activity_type_ids.data = [
                activity_type.id for activity_type in user.notified_activity_types
            ]
            self.weekdays.data = user.notification_weekday_list()

    def selected_event_types_require_activity(self) -> bool:
        """Whether the current event type selection makes activity filters relevant."""
        if not self.event_type_ids.data:
            return True
        return any(
            event_type_id in self.event_type_requires_activity_ids
            for event_type_id in self.event_type_ids.data
        )

    def normalized_activity_type_ids(self) -> list[int]:
        """Return only activity filters that are compatible with selected event types."""
        if self.event_type_ids.data and not self.selected_event_types_require_activity():
            return []
        return self.activity_type_ids.data or []
