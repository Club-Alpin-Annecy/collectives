""" Module for reservation related route

This modules contains the /reservation Blueprint
"""
import datetime
from flask_login import current_user
from flask import render_template, redirect, url_for
from flask import Blueprint, flash

from collectives.models.role import RoleIds
from collectives.utils.access import valid_user, confidentiality_agreement, user_is

from ..models import db, Equipment, EquipmentType, EquipmentModel, Reservation

blueprint = Blueprint("reservation", __name__, url_prefix="/reservation")
""" Equipment blueprint

This blueprint contains all routes for reservations and equipment
"""
@blueprint.route("/", methods=["GET"])
def reservation():
    """
    Show all the reservations
    """
    reservation = Reservation()
    
    return render_template(
        "reservation/reservations.html",
        reservation
    )
