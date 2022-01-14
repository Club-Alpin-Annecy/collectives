""" Module for reservation related route

This modules contains the /reservation Blueprint
"""
from datetime import datetime
from flask_login import current_user
from flask import render_template, redirect, url_for
from flask import Blueprint, flash
from ..models import db
from ..models.event import Event
from ..models.reservation import ReservationStatus, Reservation
from ..models.role import RoleIds
from ..forms.reservation import LeaderReservationForm

blueprint = Blueprint("reservation", __name__, url_prefix="/reservation")
""" Reservation blueprint

This blueprint contains all routes for reservations
"""


@blueprint.route("/", methods=["GET"])
def reservation():
    """
    Show all the reservations
    """
    return render_template(
        "reservation/reservation.html",
    )


@blueprint.route("/add", methods=["GET"])
@blueprint.route("/<int:reservation_id>", methods=["GET"])
def manage_reservation(reservation_id=None):
    """doc"""
    reservation = (
        Reservation()
        if reservation_id is None
        else Reservation.query.get(reservation_id)
    )

    form = (
        LeaderReservationForm()
        if reservation_id is None
        else LeaderReservationForm(obj=reservation)
    )
    action = "Ajout" if reservation_id is None else "Édition"

    if not form.validate_on_submit():
        return render_template(
            "basicform.html",
            form=form,
            title=f"{action} de réservation",
        )

    form.populate_obj(reservation)

    db.session.add(reservation)
    db.session.commit()

    return redirect(url_for("reservation.reservation"))


@blueprint.route("/<int:event_id>/<int:role_id>/register", methods=["GET"])
def register(event_id=None, role_id=None):
    role = RoleIds.get(role_id)
    if role is None:
        flash("Role inexistant", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    if not role.relates_to_activity():
        flash("Role insuffisant", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    event = Reservation() if event_id is None else Event.query.get(event_id)
    form = LeaderReservationForm()

    if not form.validate_on_submit():
        return render_template(
            "basicform.html",
            form=form,
            event=event,
            title=f"Réservation",
        )


def create_demo_values():
    """
    Initiate the DB : put fake data to simulate what the pages would look like
    """
    reservations = [
        ["12/01/22", "21/01/22", ReservationStatus.Ongoing, False, 1, 1],
        ["01/01/22", "22/01/22", ReservationStatus.Ongoing, True, 2, 0],
        ["12/01/22", None, ReservationStatus.Planned, False, 3, 1],
        ["30/12/21", "10/01/22", ReservationStatus.Completed, False, 1, 0],
    ]

    for resi in reservations:
        res = Reservation()
        res.collect_date = datetime.strptime(resi[0], "%d/%m/%y")
        if resi[1] != None:
            res.return_date = datetime.strptime(resi[1], "%d/%m/%y")
        res.status = resi[2]
        res.extended = resi[3]
        res.user_id = resi[4]
        res.event_id = resi[5]
        db.session.add(res)
        db.session.commit()
