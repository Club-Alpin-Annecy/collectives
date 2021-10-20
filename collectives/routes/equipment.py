""" Module for equipment related route

This modules contains the /equipment Blueprint
"""
from flask import flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint, escape
from flask_login import current_user

from collectives.models.equipment import EquipmentType

from ..forms.equipment import AddEquipmentTypeForm

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




@blueprint.route("/equipment_type", methods=["GET", "POST"])
def view_equipment_type():
    
    listEquipementType = EquipmentType.query.all()
    # equipments.commit()


    # for aEquipement in allEquipment:
    #     print(aEquipement.type_name)

    # listEquipementType = []
    # listEquipmentName = ["Baudrier", "Crampon", "Crocs"]

    # for equipementName in listEquipmentName:
    #     equipmentType = EquipmentType()
    #     equipmentType.type_name = equipementName

    #     listEquipementType.append(equipmentType)


    # print(vars(equipment), flush=True)

    form = AddEquipmentTypeForm()

    if form.validate_on_submit():

        new_equipment_type = EquipmentType()

        new_equipment_type.type_name = form.libelleEquipmentType.data
        new_equipment_type.price = float(form.priceEquipmentType.data)


        db.session.add(new_equipment_type)
        listEquipementType.append(new_equipment_type)
        db.session.commit()


    test = EquipmentType.query.all()
    print(test)

  

    for aEquipement in test:
        print(aEquipement.type_name)

    return render_template(
        "equipment_type.html",
        # equipments=equipments
        # equipment=equipment,
        listEquipementType=listEquipementType,
        form=form

    )




@blueprint.route("/stock", methods=["GET"])
def view_equipment_stock():
    # equipments = Equipment.query.all()
    # equipments.commit()

    equipment = Equipment()
    equipment.purchaseDate = datetime.datetime.now()
    equipment.reference = "blabla"
    equipment.caution = 12.1
    equipment.purchasePrice = 15.50


    return render_template(
        "equipment_stock.html",
        # equipments=equipments
        equipment=equipment,
    )




