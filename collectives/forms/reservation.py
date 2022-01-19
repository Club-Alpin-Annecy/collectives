from wtforms import DateField, SubmitField
from flask_wtf.form import FlaskForm
from ..models.reservation import Reservation


class LeaderReservationForm(FlaskForm):
    """Form for leaders to reserve equipment
    Contrary to lambda user, they don't need to pay nor specify a return date
    """

    class Meta:
        model = Reservation

    collect_date = DateField("Date d'emprunt", format="%d/%m/%Y")

    submit = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ReservationToLocationForm(FlaskForm):
    """Form for deleting an equipment"""

    validate = SubmitField("Valider la réservation")
