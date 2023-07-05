""" Module for activity type related forms"""

from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, Label
from wtforms.validators import DataRequired

from collectives.models import ActivityType


class ActivityTypeSelectionForm(FlaskForm):
    """Form to select an activity type"""

    activity_id = SelectField("Activité", coerce=int, validators=[DataRequired()])
    """ Activity selection field"""
    submit = SubmitField("Selectionner")

    def __init__(self, *args, **kwargs):
        """Overloaded constructor populating activity list.

        Usable KW args:

        - activity_list : set the list of selectionnable activity
        - submit_label : change default text of submit button
        - all_enabled (boolean): add a (-1, "All") entry to select all activities
        """
        super().__init__(*args, **kwargs)

        activity_list = kwargs.get("activity_list", ActivityType.query.all())

        self.activity_id.choices = [(a.id, a.name) for a in activity_list]

        all_enabled = kwargs.get("all_enabled", False)

        if all_enabled:
            self.activity_id.choices.append((-1, "All"))

        if "submit_label" in kwargs:
            self.submit.label = Label(self.submit.id, kwargs["submit_label"])
