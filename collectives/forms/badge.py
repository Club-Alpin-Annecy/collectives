"""Module containing forms for updating user information"""

from datetime import date

from flask import request
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import (
    FieldList,
    HiddenField,
    SelectField,
    StringField,
    SubmitField,
    FileField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    ValidationError,
)
from wtforms_alchemy import ModelForm

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.forms.order import OrderedModelForm
from collectives.forms.utils import coerce_optional
from collectives.models import (
    ActivityType,
    Badge,
    BadgeCustomLevel,
    BadgeIds,
)


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


class BadgeForm(OrderedModelForm, ActivityTypeSelectionForm):
    """Form for administrators to add badges to users"""

    class Meta:
        """Fields to expose"""

        model = Badge
        exclude = ["creation_time"]

    submit = SubmitField("Ajouter")

    level = SelectField("Niveau", choices=[], coerce=coerce_optional(int))

    field_order = ["badge_id", "activity_id", "level", "*"]

    def __init__(self, *args, badge_ids: list[BadgeIds] = None, **kwargs):
        """Overloaded constructor populating activity list"""

        if "no_enabled" not in kwargs:
            kwargs["no_enabled"] = True

        super().__init__(*args, **kwargs)

        if not badge_ids:
            badge_ids = list(BadgeIds)
        self.badge_id.choices = [
            (badge_id.value, badge_id.display_name()) for badge_id in badge_ids
        ]

        if "expiration_date" not in request.form:
            badge = kwargs.get("obj", None)
            if badge:
                self.expiration_date.data = compute_default_expiration_date(
                    badge.badge_id, badge.level
                )
            else:
                self.expiration_date.data = compute_default_expiration_date()

        if self.badge_id.data:
            if self.badge_id.data.requires_level():
                levels = self.badge_id.data.levels()
                self.level.choices = [(k, desc.name) for k, desc in levels.items()]
            else:
                if self.level.data:
                    self.level.choices = [(self.level.data, self.level.data)]
                else:
                    self.level.choices = [("", "Aucun")]
                self.level.validate_choice = False

    def validate_activity_id(self, field):
        """WTFForms validator function that make sure the activity_id field is not set
        if the selected badge is not related to an activity"""
        badge_id = self.badge_id.coerce(self.badge_id.data)
        if badge_id is not None:
            if not badge_id.accepts_activity():
                field.data = None
            if badge_id.requires_activity() and not field.data:
                raise ValidationError(
                    "Ce type de badge nécessite une activité associée."
                )

    def validate_level(self, field):
        """WTFForms validator function that make sure the level is consistent"""
        badge_id = BadgeIds(int(self.badge_id.data))
        levels = badge_id.levels()

        if not badge_id.requires_level():
            return

        level = self.level.coerce(field.data)
        if level not in levels:
            raise ValidationError(f"Niveau invalide: {level}")

        level_desc = levels[level]
        if not level_desc.is_compatible_with_activity(self.activity_id.data):
            raise ValidationError(
                f"Le choix '{level_desc.name}' est spécifique à l'activité '{level_desc.activity_name()}'"
            )


class RenewBadgeForm(ModelForm, FlaskForm):
    """Form for administrators to add badges to users"""

    class Meta:
        """Fields to expose"""

        model = Badge
        only = ["expiration_date"]

    submit = SubmitField("Renouveler")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if "expiration_date" not in request.form:
            badge = kwargs.get("obj", None)
            if badge:
                self.expiration_date.data = compute_default_expiration_date(
                    badge.badge_id, badge.level
                )
            else:
                self.expiration_date.data = compute_default_expiration_date()


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

    csv_file = FileField("ou fichier CSV")

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


class CompetencyBadgeForm(ActivityTypeSelectionForm):
    """Form for leaders to add practitioner badges to users"""

    level = SelectField(
        "Niveau",
        coerce=int,
        validators=[InputRequired()],
        choices=[],
    )

    def __init__(self, badge_id: BadgeIds, *args, **kwargs):
        """Overloaded constructor populating activity list"""

        led_activities = {
            a.id: a for a in current_user.get_organizable_activities(need_leader=True)
        }

        super().__init__(
            activity_list=led_activities.values(),
            submit_label="Attribuer",
            *args,
            **kwargs,
        )

        self.badge_id = badge_id
        self.submit.name = str(badge_id)

        if badge_id == BadgeIds.Practitioner:
            self.level.choices = [(0, "Aucun")] + [
                (k, f"{desc.name} ({desc.abbrev})")
                for k, desc in badge_id.levels().items()
                if desc.activity_id is None or desc.activity_id in led_activities
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
        exclude = ["badge_id", "level"]

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


class BadgeCustomPractitionerLevelForm(ActivityTypeSelectionForm):
    """Form for setting custom names for practitioner badge levels"""

    level_names = FieldList(
        label="Intitulés des niveaux de pratique",
        unbound_field=StringField(),
        min_entries=len(BadgeIds.Practitioner.levels()),
        max_entries=len(BadgeIds.Practitioner.levels()),
    )

    def __init__(self, activity_list, *args, **kwargs):
        """Overloaded  constructor"""

        super().__init__(
            *args, activity_list=activity_list, submit_label="Modifier", **kwargs
        )

        default_levels = BadgeIds.Practitioner.levels()
        for level_name, (level, level_desc) in zip(
            self.level_names, default_levels.items()
        ):
            level_name.label = level_desc.name
            level_name.id = f"{self.level_names.id}-{level}"
            level_name.name = f"{self.level_names.id}-{level}"
            if not request.form:
                level_name.data = level_desc.name
