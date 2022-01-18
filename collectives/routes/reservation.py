""" Module for reservation related route

This modules contains the /reservation Blueprint
"""
import datetime
from flask_login import current_user
from flask import render_template
from flask import Blueprint
from collectives.models.reservation import ReservationLine

from ..models import db, EquipmentType, Reservation

blueprint = Blueprint("reservation", __name__, url_prefix="/reservation")
""" Equipment blueprint

This blueprint contains all routes for reservations and equipment
"""


@blueprint.route("/", methods=["GET"])
def reservations():
    """
    Show all the reservations
    """
    aReservation = Reservation()

    aReservation.collect_date = datetime.datetime.now()
    aReservation.return_date = datetime.datetime.now()
    aReservation.user = current_user
    for y in range(1, 5):
        aReservationLine = ReservationLine()
        aReservationLine.quantity = y
        aReservationLine.equipmentType = EquipmentType.query.get(y)
        aReservation.lines.append(aReservationLine)
    db.session.add(aReservation)

    return render_template(
        "reservation/reservations.html",
        reservations=Reservation.query.all(),
    )


@blueprint.route("/<int:reservation_id>", methods=["GET"])
def reservation(reservation_id):
    """
    Show a reservation
    """

    return render_template(
        "reservation/reservation.html",
        reservation=Reservation.query.get(reservation_id),
    )


@blueprint.route("/line/<int:reservationLine_id>", methods=["GET"])
def reservationLine(reservationLine_id):
    """
    Show a reservation line
    """

    return render_template(
        "reservation/reservationLine.html",
        reservationLine=ReservationLine.query.get(reservationLine_id),
    )
