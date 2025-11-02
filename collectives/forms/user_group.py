"""Module containing form widgets for editing user groups"""

import json
from typing import Callable, Optional, TypeVar, Union

from flask import url_for
from markupsafe import Markup
from wtforms import (
    BooleanField,
    FieldList,
    FormField,
    HiddenField,
    IntegerField,
    SelectField,
    SelectMultipleField,
)
from wtforms.validators import Optional as OptionalValidator
from wtforms.validators import ValidationError
from wtforms_alchemy import ModelForm

from collectives.forms.utils import coerce_optional
from collectives.models import ActivityType, BadgeIds, Configuration, Event, RoleIds, db
from collectives.models.user_group import (
    GroupBadgeCondition,
    GroupEventCondition,
    GroupLicenseCondition,
    GroupRoleCondition,
    UserGroup,
)

T = TypeVar("T")
""" Type variable for typing annotations """


def _empty_string_if_none(value: Optional[T]) -> Union[T, str]:
    """
    :param value: input value
    :returns: the empty string if the input value is None, the unmodified input value otherwise
    """
    if value is None:
        return ""
    return value


class GroupRoleConditionForm(ModelForm):
    """Form for creating role conditions in user group forms"""

    class Meta:
        """Fields to expose"""

        model = GroupRoleCondition
        only = ["invert"]

    condition_id = HiddenField()

    role_id = SelectField("Rôle", coerce=coerce_optional(RoleIds.coerce))
    activity_id = SelectField("Activité", coerce=coerce_optional(int))

    delete = BooleanField("Supprimer")

    def __init__(self, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        if "obj" in kwargs:
            self.condition_id.data = kwargs["obj"].id

        self.activity_id.choices = [("", "N'importe quelle activité")] + [
            (activity.id, activity.name) for activity in ActivityType.get_all_types()
        ]
        self.role_id.choices = [("", "N'importe quel rôle"), *RoleIds.choices()]

    def activity(self) -> Optional[ActivityType]:
        """:returns: the activity corresponding to the current activity_id"""
        if self.activity_id.data:
            return db.session.get(ActivityType, self.activity_id.data)
        return None

    def activity_name(self) -> str:
        """:returns: the name of the activity if it is not None, a default text otherwise"""
        activity = self.activity()
        return "N'importe quelle activité" if not activity else activity.name

    def role_name(self) -> str:
        """:returns: the name of the role if it is not None, a default text otherwise"""
        if self.role_id.data:
            return RoleIds.display_name(RoleIds(self.role_id.data))
        return "N'importe quel rôle"

    def validate_activity_id(self, field):
        """WTFForms validator function that make sure the activity_id field is not set
        if the selected role is not related to an activity"""
        role_id = self.role_id.coerce(self.role_id.data)
        if role_id is not None and not role_id.relates_to_activity():
            field.data = None


class GroupBadgeConditionForm(ModelForm):
    """Form for creating badge conditions in user group forms"""

    class Meta:
        """Fields to expose"""

        model = GroupBadgeCondition
        only = ["invert"]

    condition_id = HiddenField()

    badge_id = SelectField("Badge", coerce=coerce_optional(BadgeIds.coerce))
    activity_id = SelectField("Activité", coerce=coerce_optional(int))
    level = IntegerField("Niveau", validators=[OptionalValidator()])

    delete = BooleanField("Supprimer")

    def __init__(self, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        if "obj" in kwargs:
            self.condition_id.data = kwargs["obj"].id

        self.activity_id.choices = [("", "N'importe quelle activité")] + [
            (activity.id, activity.name) for activity in ActivityType.get_all_types()
        ]
        self.badge_id.choices = [("", "N'importe quel badge"), *BadgeIds.choices()]

    def activity(self) -> Optional[ActivityType]:
        """:returns: the activity corresponding to the current activity_id"""
        if self.activity_id.data:
            return db.session.get(ActivityType, self.activity_id.data)
        return None

    def activity_name(self) -> str:
        """:returns: the name of the activity if it is not None, a default text otherwise"""
        activity = self.activity()
        return "N'importe quelle activité" if not activity else activity.name

    def badge_name(self) -> str:
        """:returns: the name of the badge if it is not None, a default text otherwise"""
        if self.badge_id.data:
            return BadgeIds.display_name(BadgeIds(self.badge_id.data))
        return "N'importe quel rôle"

    def level_name(self) -> str:
        """:returns: the name of the level if it is not None, a default text otherwise"""
        if self.badge_id.data and self.level.data:
            try:
                return (
                    BadgeIds(self.badge_id.data)
                    .level(
                        level=int(self.level.data), activity_id=self.activity_id.data
                    )
                    .name
                )
            except (ValueError, IndexError, AttributeError):
                pass
        return "Tous niveaux"

    def validate_activity_id(self, field):
        """WTFForms validator function that make sure the activity_id field is not set
        if the selected badge is not related to an activity"""
        badge_id = self.badge_id.coerce(self.badge_id.data)
        if badge_id is not None and not badge_id.accepts_activity():
            field.data = None

    def validate_level(self, field):
        """WTFForms validator function that make sure the level field is not set
        if the selected badge has not meaningful levels"""
        badge_id: BadgeIds = self.badge_id.coerce(self.badge_id.data)
        if badge_id is None:
            # No level restriction is possible
            field.data = None
            return

        levels = badge_id.levels()
        if not levels and not badge_id.requires_level():
            # No meaningful levels for this badge, ignore
            field.data = None
            return

        if not field.data:
            if badge_id.requires_level():
                raise ValidationError(
                    f"Le badge {badge_id.display_name()} doit être précisé"
                )
            field.data = None
            return

        level = int(field.data)
        if level not in levels:
            raise ValidationError(
                f"Niveau invalide pour le badge {badge_id.display_name()}"
            )

        level_desc = levels[level]

        if level_desc.activity_id is not None and not self.activity_id.data:
            self.activity_id.data = level_desc.activity_id

        if not level_desc.is_compatible_with_activity(self.activity_id.data):
            raise ValidationError(
                f"Le choix '{level_desc.name}' est incompatible avec l'activité sélectionnée '{self.activity_name()}'"
            )


class GroupEventConditionForm(ModelForm):
    """Form for creating event conditions in user group forms"""

    class Meta:
        """Fields to expose"""

        model = GroupEventCondition
        only = ["invert"]

    condition_id = HiddenField()

    event_id = IntegerField("Événement")
    is_leader = SelectField("Rôle", coerce=coerce_optional(int))

    def __init__(self, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        if "obj" in kwargs:
            self.condition_id.data = kwargs["obj"].id

        self.is_leader.choices = [
            ("", "Encadrant ou Participant"),
            (False, "Participant"),
            (True, "Encadrant"),
        ]

    def event(self) -> Optional[Event]:
        """:returns: the event associated with the condition"""
        if self.event_id.data:
            return db.session.get(Event, self.event_id.data)
        return None


class UserGroupForm(ModelForm):
    """Form for editing user group conditions"""

    class Meta:
        """Fields to expose"""

        model = UserGroup
        only = []

    role_conditions = FieldList(
        label="Restrictions par rôle",
        unbound_field=FormField(GroupRoleConditionForm, default=GroupRoleCondition),
    )
    badge_conditions = FieldList(
        label="Restrictions par badge",
        unbound_field=FormField(GroupBadgeConditionForm, default=GroupBadgeCondition),
    )
    event_conditions = FieldList(
        label="Restrictions par événement",
        unbound_field=FormField(GroupEventConditionForm, default=GroupEventCondition),
    )

    new_event_is_leader = SelectField("Rôle", coerce=coerce_optional(int))

    license_conditions = SelectMultipleField("Types de licence")
    license_invert = SelectField("Négation", coerce=int, default=0)

    new_role_id = SelectField("Rôle", coerce=coerce_optional(RoleIds.coerce))
    new_role_activity_id = SelectField("Activité", coerce=coerce_optional(int))

    new_badge_id = SelectField("Badge", coerce=coerce_optional(BadgeIds.coerce))
    new_badge_activity_id = SelectField("Activité", coerce=coerce_optional(int))
    new_badge_level = IntegerField("Niveau", validators=[OptionalValidator()])

    def __init__(self, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        if "prefix" in kwargs:
            self.prefix = kwargs["prefix"]

        user_group = kwargs.get("obj", None)
        formdata = kwargs.get("formdata", None)
        if user_group and not formdata:
            self.license_conditions.data = [
                cond.license_category for cond in user_group.license_conditions
            ]
            if user_group.license_conditions:
                self.license_invert.data = int(user_group.license_conditions[0].invert)

        self.license_conditions.choices = [
            (cat, f"{cat} — {descr}")
            for cat, descr in Configuration.LICENSE_CATEGORIES.items()
        ]

        self.new_role_id.choices = [("", "N'importe quel rôle"), *RoleIds.choices()]
        self.new_role_activity_id.choices = [("", "N'importe quelle activité")] + [
            (activity.id, activity.name) for activity in ActivityType.get_all_types()
        ]

        self.new_badge_id.choices = [("", "N'importe quel badge"), *BadgeIds.choices()]
        self.new_badge_activity_id.choices = [("", "N'importe quelle activité")] + [
            (activity.id, activity.name) for activity in ActivityType.get_all_types()
        ]

        self.new_event_is_leader.choices = [
            ("", "Encadrants ou Participants"),
            (int(False), "Participants"),
            (int(True), "Encadrants"),
        ]
        self.license_invert.choices = [
            (int(False), "Autoriser"),
            (int(True), "Refuser"),
        ]

    def validate_license_conditions(self, field):
        """WTFForms validators that converts license_category input as a list of strings
        to a list of GroupLicenseCondition objects"""

        valid_types = Configuration.LICENSE_CATEGORIES
        for license_type in field.data:
            if license_type not in valid_types:
                raise ValidationError(
                    f"'{license_type}' n'est pas une catégorie de licence FFCAM valide."
                )

        if field.data:
            field.data = [
                GroupLicenseCondition(
                    license_category=cat, invert=self.license_invert.data
                )
                for cat in field.data
            ]

    def event_conditions_as_json(self) -> str:
        """:returns: the current event condition form values as a JSON string
        for creating JS entries"""

        event_conditions = [
            {
                "id": id,
                "condition_id": _empty_string_if_none(condition_form.condition_id.data),
                "event_id": _empty_string_if_none(condition_form.event_id.data),
                "event_name": Markup(condition_form.event().title),
                "event_url": url_for(
                    "event.view_event",
                    event_id=condition_form.event_id.data,
                ),
                "is_leader": _empty_string_if_none(condition_form.is_leader.data),
                "invert": condition_form.invert.data,
            }
            for id, condition_form in enumerate(self.event_conditions)
        ]
        return json.dumps(event_conditions)

    def role_conditions_as_json(self) -> str:
        """:returns: the current role condition form values as a JSON string
        for creating JS entries"""

        role_conditions = [
            {
                "id": id,
                "condition_id": _empty_string_if_none(condition_form.condition_id.data),
                "role_id": _empty_string_if_none(condition_form.role_id.data),
                "role_name": Markup(condition_form.role_name()),
                "activity_id": _empty_string_if_none(condition_form.activity_id.data),
                "activity_name": Markup(condition_form.activity_name()),
                "invert": condition_form.invert.data,
            }
            for id, condition_form in enumerate(self.role_conditions)
        ]
        return json.dumps(role_conditions)

    def badge_conditions_as_json(self) -> str:
        """:returns: the current badge condition form values as a JSON string
        for creating JS entries"""

        badge_conditions = [
            {
                "id": id,
                "condition_id": _empty_string_if_none(condition_form.condition_id.data),
                "badge_id": _empty_string_if_none(condition_form.badge_id.data),
                "badge_name": Markup(condition_form.badge_name()),
                "activity_id": _empty_string_if_none(condition_form.activity_id.data),
                "activity_name": Markup(condition_form.activity_name()),
                "level": _empty_string_if_none(condition_form.level.data),
                "level_name": Markup(condition_form.level_name()),
                "invert": condition_form.invert.data,
            }
            for id, condition_form in enumerate(self.badge_conditions)
        ]
        return json.dumps(badge_conditions)
