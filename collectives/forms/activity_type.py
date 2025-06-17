"""Module for activity type related forms"""

from typing import List

from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, Label, Field
from wtforms.validators import InputRequired
from wtforms_alchemy import ModelForm


from collectives.models import ActivityType


class ActivityTypeSelectionForm(FlaskForm):
    """Form to select an activity type"""

    ALL_ACTIVITIES = 999999
    """ Id for all activity choice in `activity_id`"""

    NO_ACTIVITY = 0
    """ Id for all activity choice in `activity_id`"""

    activity_id = SelectField("Activité", coerce=int, validators=[InputRequired()])
    """ Activity selection field"""
    submit = SubmitField("Selectionner")

    def validate_activity_id(self, field: Field):
        """Sets activity_id to None if it was set to NO_ACTIVITY"""
        if field.data == ActivityTypeSelectionForm.NO_ACTIVITY:
            field.data = None

    def __init__(
        self,
        *args,
        all_enabled: bool = False,
        no_enabled: bool = False,
        activity_list: List[ActivityType] = None,
        submit_label: str = None,
        **kwargs
    ):
        """Overloaded constructor populating activity list.

        :param activity_list: set the list of selectionnable activity
        :param submit_label: change default text of submit button
        :param all_enabled: add a ("All") entry to select all activities
        :param no_enabled: add a ("No") entry to select no activity
        """
        super().__init__(*args, **kwargs)

        activity_list = activity_list or ActivityType.get_all_types()

        self.activity_id.choices = [
            (a.id, a.name) for a in activity_list if not a.deprecated
        ]

        if all_enabled:
            self.activity_id.choices.append((self.ALL_ACTIVITIES, "Toutes activités"))
        if no_enabled:
            self.activity_id.choices.insert(0, (self.NO_ACTIVITY, "Pas d'activité"))

        if submit_label:
            self.submit.label = Label(self.submit.id, submit_label)


class ActivityTypeEditForm(ModelForm, FlaskForm):
    """Form to modify an activity type."""

    class Meta:
        """Fields to expose"""

        model = ActivityType
        exclude = ["short", "kind"]

    submit = SubmitField("Modifier")


class ActivityTypeCreationForm(ModelForm, FlaskForm):
    """Form to create an activity type."""

    class Meta:
        """Fields to expose"""

        model = ActivityType
        exclude = ["kind"]

    submit = SubmitField("Ajouter")
