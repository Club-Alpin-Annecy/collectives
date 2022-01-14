from collectives.models.role import RoleIds

from ..models.user import User
from ..models.reservation import Reservation
from wtforms import DateField, SelectField, SubmitField
from flask_wtf.form import FlaskForm


class LeaderReservationForm(FlaskForm):
    """Form for leaders to reserve equipment
    Contrary to lambda user, they don't need to pay nor specify a return date
    """

    class Meta:
        model = Reservation

    leader_id = SelectField("Encadrant :", coerce=int, choices=[])

    event_id = SelectField("Collective :", coerce=int, choices=[])

    collect_date = DateField("Date d'emprunt :", format="%d/%m/%Y")

    submit = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.leader_id.choices = User.query.filter_by(
            User.roles in RoleIds.all_activity_leader_roles()
        ).all()
