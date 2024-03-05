""" Module for equipment reservation forms"""

from datetime import datetime
from wtforms import SubmitField, HiddenField

from flask_wtf.form import FlaskForm
from wtforms_alchemy import ModelForm

from collectives.models import Reservation


class ReservationForm(FlaskForm, ModelForm):
    """Form to create an equipment reservation"""

    class Meta:
        """Fields to expose"""

        model = Reservation
        include = ["collect_date"]

    submit = SubmitField("Enregistrer")
    event = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "event" in kwargs and kwargs["event"] is not None:
            self.event = kwargs["event"]
            self.collect_date.data = self.event.start
        else:
            self.collect_date.data = datetime.now()


class LeaderReservationForm(ReservationForm):
    """Form for leaders to reserve equipment
    Contrary to lambda user, they don't need to pay nor specify a return date
    """


class ReservationToRentalForm(FlaskForm):
    """Form to change the status of a rental to OnGoing"""

    validate = SubmitField("Valider la réservation")


class EndRentalForm(FlaskForm):
    """Form to end a rental"""

    validate = SubmitField("Valider le retour de la location")


class AddEquipmentInReservationForm(FlaskForm):
    """Form to add an equipment in a reservation"""

    add_equipment = HiddenField("Ajouter un équipement")


class NewRentalUserForm(FlaskForm):
    """Form to put an user for a rental from no reservation"""

    user = HiddenField("Nom d'adhérent")


class NewRentalEquipmentForm(FlaskForm):
    """Form to put a new equipment for a rental from no reservation"""

    add_equipment = HiddenField("Référence équipement")


class CancelRentalForm(FlaskForm):
    """Form to cancel a new rental from no reservation"""

    cancel = SubmitField("Annuler")
