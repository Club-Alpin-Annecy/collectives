""" Module for equipment related route

This modules contains the /equipment Blueprint
"""
from flask import flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint, escape
from flask_login import current_user

from ..models import db, User

from ..utils.access import confidentiality_agreement, valid_user


blueprint = Blueprint("collectives", __name__, url_prefix="/equipment")
""" Event blueprint

This blueprint contains all routes for reservations and equipment
"""


@blueprint.route("/equipment", methods=["GET"])
def view_equipment():
    # equipments = Equipment.query.all()
    # equipments.commit()
    users = User.query.all()
    return render_template(
        "equipment.html",
        # equipments=equipments
        users=users,
    )
