""" Module for reservation related route

This modules contains the /reservation Blueprint
"""
import datetime
from flask_login import current_user
from flask import render_template, redirect, url_for
from flask import Blueprint, flash
from collectives.models.reservation import ReservationLine

from collectives.models.role import RoleIds
from collectives.utils.access import valid_user, confidentiality_agreement, user_is

from ..models import db, Equipment, EquipmentType, EquipmentModel, Reservation

blueprint = Blueprint("reservation", __name__, url_prefix="/reservation")
""" Equipment blueprint

This blueprint contains all routes for reservations and equipment
"""
@blueprint.route("/", methods=["GET"])
def reservations():
    """
    Show all the reservations
    """
    reservation = Reservation()
    
    reservation.collect_date = datetime.datetime.now()
    reservation.return_date = datetime.datetime.now()
    reservation.user = current_user
    for y in range(1,5):
        reservationLine = ReservationLine()
        reservationLine.quantity = y
        reservationLine.equipment = Equipment.query.get(y)
        reservation.lines.append(reservationLine)
    db.session.add(reservation)
    
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
        reservation=Reservation.query.get(reservation_id)
    )
