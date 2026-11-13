"""Module containing forms related to retex"""

from typing import List, Tuple

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    Field,
    HiddenField,
    RadioField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
from wtforms.validators import InputRequired, Optional, ValidationError
from wtforms_alchemy import ModelForm

from collectives.models import ActivityType, Retex, RetexStatus


class RetexForm(ModelForm, FlaskForm):
    """Form to create or modify a retex."""

    class Meta:
        """Fields to expose"""

        model = Retex
        only = ["status", "description"]

    # No level is preselected, so that leaders choose it. An unknown value is
    # still refused: RetexStatus.coerce fails on it.
    status = RadioField(
        "Niveau",
        choices=RetexStatus.choices(),
        coerce=RetexStatus.coerce,
        validate_choice=False,
        validators=[InputRequired("Choisissez le niveau du RETEX.")],
    )

    submit = SubmitField("Enregistrer")

    def status_levels(self, event_retex: bool) -> List[Tuple[Field, RetexStatus]]:
        """Pairs the radio buttons of the status field with their level.

        :param event_retex: whether to return the event retex levels or the
            learning retex levels.
        :return: list of (radio button, level) tuples
        """
        levels = [(subfield, RetexStatus(subfield.data)) for subfield in self.status]
        return [
            (subfield, level)
            for subfield, level in levels
            if level.is_event_retex() == event_retex
        ]


class RetexExportForm(FlaskForm):
    """Form to filter the retex Excel export."""

    activity_ids = SelectMultipleField("Activités", coerce=int)
    status_ids = SelectMultipleField(
        "Niveau du retex", choices=RetexStatus.choices(), coerce=RetexStatus.coerce
    )
    date_from = DateField("Depuis le", validators=[Optional()])
    date_to = DateField("Jusqu'au", validators=[Optional()])
    leader_id = HiddenField()
    leader_search = StringField(
        "Encadrant",
        render_kw={
            "autocomplete": "off",
            "class": "search-input",
            "placeholder": "Tous les encadrants…",
        },
    )
    submit = SubmitField("Générer Excel")

    def __init__(self, *args, activity_list: List[ActivityType] = None, **kwargs):
        super().__init__(*args, **kwargs)
        activity_list = activity_list or []
        self.activity_ids.choices = [(a.id, a.name) for a in activity_list]

    def validate_date_to(self, field):
        """Ensure the end date is not before the start date."""
        if self.date_from.data and field.data and field.data < self.date_from.data:
            raise ValidationError(
                "La date de fin doit être postérieure à la date de début."
            )
