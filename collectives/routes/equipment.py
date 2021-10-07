""" Module for equipment related route

This modules contains the /equipment Blueprint
"""
from flask import flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint, escape
from flask_login import current_user

import datetime

from ..models import db, User, Equipment

from ..utils.access import confidentiality_agreement, valid_user


blueprint = Blueprint("equipment", __name__, url_prefix="/equipment")
""" Event blueprint

This blueprint contains all routes for reservations and equipment
"""


@blueprint.route("/", methods=["GET"])
def view_equipment():
    # equipments = Equipment.query.all()
    # equipments.commit()

    equipment = Equipment()
    equipment.purchaseDate = datetime.datetime.now()
    equipment.reference = "blabla"
    equipment.caution = 12.1
    equipment.purchasePrice = 15.50

    print(vars(equipment), flush=True)

    return render_template(
        "equipment.html",
        # equipments=equipments
        equipment=equipment,
    )



@blueprint.route("/add", methods=["GET"])
def Test_equipment():
    # equipments = Equipment.query.all()
    # equipments.commit()

    equipment = Equipment()
    equipment.purchaseDate = datetime.datetime.now()
    equipment.reference = "blabla"
    equipment.caution = 12.1
    equipment.purchasePrice = 15.50

    print(vars(equipment), flush=True)

    return render_template(
        "equipment.html",
        # equipments=equipments
        equipment=equipment,
    )