from datetime import datetime, timedelta
from wtforms import SubmitField, HiddenField

from flask_wtf.form import FlaskForm
from wtforms_alchemy import ModelForm
from ..models.reservation import Reservation


class LeaderReservationForm(FlaskForm, ModelForm):
    """Form for leaders to reserve equipment
    Contrary to lambda user, they don't need to pay nor specify a return date
    """

    class Meta:
        model = Reservation
        include = ["collect_date"]

    submit = SubmitField("Enregistrer")
    event = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = kwargs["obj"]
        self.collect_date.data = (self.event.start).replace(
            hour=(datetime.now() + timedelta(hours=1)).hour,
            minute=0,
        )


class ReservationToLocationForm(FlaskForm):
    """Form for deleting an equipment"""

    validate = SubmitField("Valider la réservation")


class EndLocationForm(FlaskForm):
    """Form for deleting an equipment"""

    validate = SubmitField("Valider la retour de la location")


class AddEquipmentInReservationForm(FlaskForm):
    """Form to add an equipment in a reservation"""

    add_equipment = HiddenField("Ajouter un equipment")


class NewRentalForm(FlaskForm):
    """Form to create a new rental from no reservation"""

    user = HiddenField("Adhérent")
    add_equipment = HiddenField("Ajouter un equipment")


class CancelRentalForm(FlaskForm):
    """Form to cancel a new rental from no reservation"""

    cancel = SubmitField("Annuler")
