import json

from wtforms_alchemy import ModelForm
from wtforms import (
    SelectField,
    FieldList,
    FormField,
    BooleanField,
    HiddenField,
    IntegerField,
    SelectMultipleField,
)
from wtforms.validators import Optional

from collectives.models import ActivityType, RoleIds, Configuration
from collectives.models.user_group import (
    UserGroup,
    GroupRoleCondition,
    GroupEventCondition,
    GroupLicenseCondition,
    Event,
)

from flask import Markup, url_for


def _coerce_optional(coerce):
    return lambda item: None if item is None or item == "" else coerce(item)


def _empty_string_if_none(value):
    if value is None:
        return ""
    return value


class GroupRoleConditionForm(ModelForm):
    class Meta:
        """Fields to expose"""

        model = GroupRoleCondition
        only = []

    condition_id = HiddenField()

    role_id = SelectField("Rôle", coerce=_coerce_optional(RoleIds.coerce))
    activity_id = SelectField("Activité", coerce=_coerce_optional(int))

    delete = BooleanField("Supprimer")

    def __init__(self, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        if "obj" in kwargs:
            self.condition_id.data = kwargs["obj"].id

        self.activity_id.choices = [("", "N'importe quelle activité")] + [
            (activity.id, activity.name) for activity in ActivityType.get_all_types()
        ]

        self.role_id.choices = [("", "N'importe quel rôle")] + RoleIds.choices()

    def activity(self) -> ActivityType:
        if self.activity_id.data:
            return ActivityType.query.get(self.activity_id.data)
        return None

    def activity_name(self) -> str:
        activity = self.activity()
        return "N'importe quelle activité" if not activity else activity.name

    def role_name(self) -> str:
        if self.role_id.data:
            return RoleIds.display_name(RoleIds(self.role_id.data))
        return "N'importe quel rôle"

    def validate_activity_id(self, field):
        role_id = self.role_id.coerce(self.role_id.data)
        if role_id is not None and not role_id.relates_to_activity():
            field.data = None


class GroupEventConditionForm(ModelForm):
    class Meta:
        """Fields to expose"""

        model = GroupEventCondition
        only = []

    condition_id = HiddenField()

    event_id = IntegerField("Événement")
    is_leader = SelectField("Rôle", coerce=_coerce_optional(int))

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

    def event(self) -> Event:
        if self.event_id.data:
            return Event.query.get(self.event_id.data)
        return None


class UserGroupForm(ModelForm):
    class Meta:
        """Fields to expose"""

        model = UserGroup
        only = []

    role_conditions = FieldList(
        FormField(GroupRoleConditionForm, default=GroupRoleCondition)
    )
    event_conditions = FieldList(
        FormField(GroupEventConditionForm, default=GroupEventCondition)
    )

    license_conditions = SelectMultipleField("Types de licence")

    new_role_id = SelectField()
    new_role_activity_id = SelectField()

    def __init__(self, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        if "prefix" in kwargs:
            self.prefix = kwargs["prefix"]

        if "obj" in kwargs and not kwargs.get("formdata", None):
            user_group = kwargs["obj"]
            self.license_conditions.data = [
                cond.license_category for cond in user_group.license_conditions
            ]

        self.license_conditions.choices = [
            (cat, f"{cat} — {descr}")
            for cat, descr in Configuration.LICENSE_CATEGORIES.items()
        ]

        self.new_role_id.choices = [("", "N'importe quel rôle")] + RoleIds.choices()
        self.new_role_activity_id.choices = [("", "N'importe quelle activité")] + [
            (activity.id, activity.name) for activity in ActivityType.get_all_types()
        ]

    def validate_license_conditions(self, field):
        if field.data:
            field.data = [
                GroupLicenseCondition(license_category=cat) for cat in field.data
            ]

    def populate_conditions(self, user_group: UserGroup):

        # Remove all existing entries
        while len(self.role_conditions) > 0:
            self.role_conditions.pop_entry()
        while len(self.event_conditions) > 0:
            self.event_conditions.pop_entry()

        # Create new entries
        for condition in user_group.role_conditions:
            self.role_conditions.append_entry(condition)
        for condition in user_group.event_conditions:
            self.event_conditions.append_entry(condition)

        # Update fields
        for condition, condition_form in zip(
            user_group.role_conditions, self.role_conditions
        ):
            condition_form.condition_id.data = condition.id
        for condition, condition_form in zip(
            user_group.event_conditions, self.event_conditions
        ):
            condition_form.condition_id.data = condition.id

        self.license_conditions.data = [
            cond.license_category for cond in user_group.license_conditions
        ]

    def event_conditions_as_json(self) -> str:
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
            }
            for id, condition_form in enumerate(self.event_conditions)
        ]
        return json.dumps(event_conditions)

    def role_conditions_as_json(self) -> str:
        event_conditions = [
            {
                "id": id,
                "condition_id": _empty_string_if_none(condition_form.condition_id.data),
                "role_id": _empty_string_if_none(condition_form.role_id.data),
                "role_name": Markup(condition_form.role_name()),
                "activity_id": _empty_string_if_none(condition_form.activity_id.data),
                "activity_name": Markup(condition_form.activity_name()),
            }
            for id, condition_form in enumerate(self.role_conditions)
        ]
        return json.dumps(event_conditions)
