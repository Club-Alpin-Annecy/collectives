import datetime
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
        if "event" in kwargs and kwargs["event"] is not None:
            self.event = kwargs["event"]
            self.collect_date.data = self.event.start
        else:
            self.collect_date.data = datetime.now()


class ReservationToLocationForm(FlaskForm):
    """Form for deleting an equipment"""

    validate = SubmitField("Valider la réservation")


class EndLocationForm(FlaskForm):
    """Form for deleting an equipment"""

    validate = SubmitField("Valider le retour de la location")


class AddEquipmentInReservationForm(FlaskForm):
    """Form to add an equipment in a reservation"""

    add_equipment = HiddenField("Ajouter un équipement")


class NewRentalUserForm(FlaskForm):
    """Form to create a new rental from no reservation"""

    user = HiddenField("Nom d'adhérent")


class NewRentalEquipmentForm(FlaskForm):
    """Form to create a new rental from no reservation"""

    add_equipment = HiddenField("Référence équipement")


class CancelRentalForm(FlaskForm):
    """Form to cancel a new rental from no reservation"""

    cancel = SubmitField("Annuler")
