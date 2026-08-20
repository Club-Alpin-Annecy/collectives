"""Module containing forms related to retex"""

from typing import List

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    HiddenField,
    RadioField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
from wtforms.validators import Optional, ValidationError
from wtforms_alchemy import ModelForm

from collectives.models import ActivityType, Retex, RetexStatus


class RetexForm(ModelForm, FlaskForm):
    """Form to create or modify a retex."""

    class Meta:
        """Fields to expose"""

        model = Retex
        only = ["status", "description"]

    status = RadioField(
        "Statut", choices=RetexStatus.choices(), coerce=RetexStatus.coerce
    )

    submit = SubmitField("Enregistrer")


class RetexExportForm(FlaskForm):
    """Form to filter the retex Excel export."""

    activity_ids = SelectMultipleField("Activités", coerce=int)
    status_ids = SelectMultipleField(
        "Statut du retex", choices=RetexStatus.choices(), coerce=RetexStatus.coerce
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
