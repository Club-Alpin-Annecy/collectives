""" Module for equipment related route

This modules contains the /equipment Blueprint
"""
import datetime
from flask_login import current_user
from flask import render_template, redirect, url_for
from flask import Blueprint, flash

from collectives.models.role import RoleIds
from collectives.utils.access import valid_user, confidentiality_agreement, user_is


from ..forms.equipment import (
    EquipmentTypeForm,
    DeleteForm,
    EquipmentModelForm,
    EquipmentForm,
)

from ..models import db, Equipment, EquipmentType, EquipmentModel

blueprint = Blueprint("equipment", __name__, url_prefix="/equipment")
""" Equipment blueprint

This blueprint contains all routes for reservations and equipment
"""


@blueprint.before_request
@valid_user()
@confidentiality_agreement()
@user_is("can_manage_equipment")
def before_request():
    """Protect all of the admin endpoints.

    Protection is done by the decorator:

    - check if user is valid :py:func:`collectives.utils.access.valid_user`
    - check if user has signed the confidentiality agreement :py:func:`collectives.utils.access.confidentiality_agreement`
    - check if user is allowed to manage equipment :py:func:`collectives.utils.access.user_is`
    """
    pass


@blueprint.route("/", methods=["GET"])
def stock_situation():
    """
    Show the stock situation
    """

    return render_template(
        "equipment/gestion/equipment.html",
    )


# --------------------------------------- EQUIPMENT TYPE AND MODELS -------------------------------------------------


@blueprint.route("/equipment_type", methods=["GET", "POST"])
def display_all_type():
    """
    Show all the equipment types and a form for to add one
    """
    addingFrom = EquipmentTypeForm()
    if addingFrom.validate_on_submit():

        new_equipment_type = EquipmentType()

        new_equipment_type.name = addingFrom.name.data
        new_equipment_type.price = float(addingFrom.price.data)
        new_equipment_type.save_typeImg(addingFrom.imageType_file.data)

        db.session.add(new_equipment_type)
        db.session.commit()
        return redirect(url_for(".display_all_type"))

    list_equipmentt_type = EquipmentType.query.all()

    return render_template(
        "equipment/gestion/equipmentType/displayAll.html",
        list_equipmentt_type=list_equipmentt_type,
        addingFrom=addingFrom,
    )


@blueprint.route("/equipment_type/<int:typeId>", methods=["GET", "POST"])
def detail_equipment_type(typeId):
    """
    Show one equipment type and its models
    """
    adding_from_model = EquipmentModelForm()
    if adding_from_model.validate_on_submit():
        new_equipment_model = EquipmentModel()
        new_equipment_model.name = adding_from_model.name.data
        new_equipment_model.equipment_type_id = typeId
        db.session.add(new_equipment_model)
        db.session.commit()
        return redirect(url_for(".detail_equipment_type", typeId=typeId))

    equipmentType = EquipmentType.query.get(typeId)
    formEdit = EquipmentTypeForm(obj=equipmentType)

    if formEdit.validate_on_submit():
        equipmentType.name = formEdit.name.data
        equipmentType.price = float(formEdit.price.data)
        equipmentType.save_typeImg(formEdit.imageType_file.data)
        db.session.commit()
        return redirect(url_for(".display_all_type"))

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipmentType/displayDetail.html",
        equipmentType=equipmentType,
        adding_from_model=adding_from_model,
        formEdit=formEdit,
        deleteForm=deleteForm,
    )


@blueprint.route("/equipment_type/<int:typeId>/edit", methods=["GET", "POST"])
def edit_equipment_type(typeId):
    """
    Route to delete a specific equipment type
    """

    typeModified = EquipmentType.query.get(typeId)
    formEdit = EquipmentTypeForm(obj=typeModified)

    if formEdit.validate_on_submit():
        typeModified.name = formEdit.name.data
        typeModified.price = float(formEdit.price.data)
        typeModified.save_typeImg(formEdit.imageType_file.data)
        db.session.commit()
        return redirect(url_for(".display_all_type"))

    list_equipmentt_type = EquipmentType.query.all()
    addingFrom = EquipmentTypeForm()

    return render_template(
        "equipment/gestion/equipmentType/displayAll.html",
        list_equipmentt_type=list_equipmentt_type,
        addingFrom=addingFrom,
        formEdit=formEdit,
        typeId=typeId,
    )


@blueprint.route("/delete_equipmentType/<int:equipmentTypeId>", methods=["POST"])
def delete_equipment_type(equipmentTypeId):
    """Route to delete a specific type"""
    equipmentType = EquipmentType.query.get(equipmentTypeId)
    db.session.delete(equipmentType)
    return redirect(url_for(".stock_situation"))


@blueprint.route(
    "/equipment_type/<int:typeId>/model<int:modelId>", methods=["GET", "POST"]
)
def edit_equipment_model(typeId, modelId):
    """
    Unused route
    """
    equipmentModelModified = EquipmentModel.query.get(modelId)
    formEditModel = EquipmentModelForm(obj=equipmentModelModified)

    if formEditModel.validate_on_submit():

        equipmentModelModified.name = formEditModel.name.data
        equipmentModelModified.equipment_type_id = formEditModel.equipmentType.data
        db.session.commit()
        return redirect(url_for(".detail_equipment_type", typeId=typeId))

    typeSelected = EquipmentType.query.get(typeId)
    adding_from_model = EquipmentModelForm()
    listEquipmentModel = EquipmentModel.query.all()
    deleteFormModel = DeleteForm()
    return render_template(
        "equipment/gestion/equipmentType/displayDetail.html",
        listEquipmentModel=listEquipmentModel,
        adding_from_model=adding_from_model,
        equipmentType=typeSelected,
        formEditModel=formEditModel,
        modelId=modelId,
        deleteFormModel=deleteFormModel,
    )


# -------------------------------------------------------------------------------------------------------

# ------------------------------------------- EQUIPMENT ---------------------------------------------------


@blueprint.route("/stock", methods=["GET", "POST"])
def stock_situation_stock():
    """
    Show all the equipments
    """

    if not current_user.matching_roles(
        [RoleIds.EquipmentManager, RoleIds.Administrator]
    ):
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    addEquipmentForm = EquipmentForm()

    if addEquipmentForm.validate_on_submit():
        new_equipment = Equipment()
        new_equipment.reference = addEquipmentForm.reference.data
        new_equipment.purchaseDate = addEquipmentForm.purchaseDate.data
        new_equipment.purchasePrice = addEquipmentForm.purchasePrice.data
        new_equipment.equipment_model_id = addEquipmentForm.equipment_model_id.data
        db.session.add(new_equipment)
        db.session.commit()
        return redirect(url_for(".stock_situation_stock"))

    equipmentTypeList = EquipmentType.query.all()

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/displayAll.html",
        equipmentTypeList=equipmentTypeList,
        addEquipmentForm=addEquipmentForm,
        deleteForm=deleteForm,
    )


@blueprint.route("/stock/detail_equipment/<int:equipment_id>", methods=["GET", "POST"])
def detail_equipment(equipment_id):
    """
    Show the detail af an equipment and a form to edit it
    """
    equipmentSelected = Equipment.query.get(equipment_id)

    editEquipmentForm = EquipmentForm(obj=equipmentSelected)

    if editEquipmentForm.validate_on_submit():
        equipmentSelected.reference = editEquipmentForm.reference.data
        equipmentSelected.purchaseDate = editEquipmentForm.purchaseDate.data
        equipmentSelected.purchasePrice = editEquipmentForm.purchasePrice.data
        equipmentSelected.equipment_model_id = editEquipmentForm.equipment_model_id.data
        equipmentSelected.manufacturer = editEquipmentForm.manufacturer.data
        db.session.commit()
        return redirect(url_for(".detail_equipment", equipment_id=equipment_id))

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/displayDetail.html",
        equipment=equipmentSelected,
        deleteForm=deleteForm,
        editEquipmentForm=editEquipmentForm,
    )


# ---------------------------------------- DELETE ROUTES-------------------------------------------------


@blueprint.route("/delete_equipment/<int:equipmentId>", methods=["POST"])
def delete_equipment(equipmentId):
    """
    Route to delete a specific equipment
    """
    del_equipment = Equipment.query.get(equipmentId)
    db.session.delete(del_equipment)
    return redirect(url_for(".stock_situation_stock"))


@blueprint.route("/delete_equipmentModel/<int:modelId>", methods=["POST"])
def delete_equipment_model(modelId):
    """
    Route to delete a specific model from an equipment type
    """
    model = EquipmentModel.query.get(modelId)
    typeId = model.equipmentType.id
    db.session.delete(model)
    return redirect(url_for(".detail_equipment_type", typeId=typeId))


# ----------------------------------------------------------------------------------------------------------


def create_equipments_in_bdd():
    """
    Initiate the DB : put fake data to simulate what the pages would look like
    """
    if EquipmentType.query.all() == []:
        equipmentsTypes = {
            "DVA": {
                "DVA Evo 3 + ": [
                    "DV 03",
                    "DV 31",
                    "DV 42",
                    "DV 43",
                    "DV 44",
                    "DV 45",
                ],
                "DVA Evo 3 +": [
                    "DV 06",
                    "DV 07",
                    "DV 08",
                    "DV 09",
                    "DV 20",
                    "DV 23",
                    "DV 25",
                    "DV 27",
                    "DV 29",
                ],
                "DVA EVO 3 +": [
                    "DV 11",
                    "DV 14",
                ],
                "DVA ELEMENT MAMMUT": [
                    "DV 35",
                    "DV 36",
                    "DV 37",
                    "DV 38",
                    "DV 39",
                    "DV 66",
                ],
                "DVA ADVENCED ": [
                    "DV 50",
                    "DV 51",
                ],
                "DVA EVOLUTION + ": [
                    "DV 55",
                    "DV 56",
                    "DV 57",
                    "DV 58",
                ],
                "DVA ORTOVOX BLEU": [
                    "DV 68",
                ],
                "DVA ARVA NEO": [
                    "DV 70",
                    "DV 71",
                    "DV 72",
                    "DV 74",
                    "DV 75",
                    "DV 76",
                    "DV 77",
                    "DV 78",
                    "DV 79",
                ],
                "DVA MANNUT PULSE": [
                    "DV 91",
                ],
                "DVA PIEPS": [
                    "DV 92",
                ],
            },
            "BAUDRIER": {
                "Baudrier": [
                    "BD 01",
                    "BD 02",
                    "BD 03",
                    "BD 04",
                    "BD 05",
                ],
            },
            "LONGES": {
                "Longe camp ": [
                    "LN 01",
                    "LN 02",
                ],
                "Longe Petzl": [
                    "LN 03",
                ],
                "Longe CT climbing": [
                    "LN 04",
                    "LN 05",
                    "LN 06",
                ],
            },
            "CASQUE": {
                "Casque camp comb": [
                    "CS 01",
                    "CS 02",
                    "CS 03",
                    "CS 04",
                    "CS 05",
                    "CS 06",
                    "CS 07",
                    "CS 08",
                    "CS 09",
                    "CS 10",
                ],
            },
            "PIOLETS": {
                "piolets Scorpio ": [
                    "PL 01",
                    "PL 02",
                    "PL 03",
                    "PL 04",
                    "PL 05",
                    "PL 06",
                    "PL 07",
                    "PL 08",
                    "PL 09",
                    "PL 10",
                    "PL 11",
                    "PL 12",
                    "PL 13",
                    "PL 14",
                    "PL 15",
                ],
                "piolets Air tec EVO ": [
                    "PL 16",
                    "PL 17",
                    "PL 18",
                    "PL 19",
                    "PL 20",
                    "PL 21",
                    "PL 22",
                    "PL 23",
                    "PL 24",
                    "PL 25",
                    "PL 26",
                ],
                "piolets cascade  camp panne": [
                    "PL 27",
                    "PL 28",
                    "PL 29",
                    "PL 30",
                    "PL 40",
                    "PL 41",
                    "PL 42",
                ],
                "piolets cascade  camp marteau": [
                    "PL 31",
                    "PL 32",
                    "PL 33",
                    "PL 34",
                    "PL 35",
                    "PL 36",
                    "PL 37",
                    "PL 38",
                    "PL 43",
                    "PL 44",
                    "PL 45",
                    "PL 46",
                    "PL 47",
                ],
                "piolets CharletMocascade21": [
                    "PL 39",
                ],
                "piolet rando glacire": [
                    "PL 48",
                    "PL 49",
                    "PL 50",
                ],
            },
            "BATONS MARCHE NORDIQUE": {
                "Batons forza 115": [
                    "BN 02",
                ],
                "Batons spirit tlscopiques": [
                    "BN 03",
                ],
                "Batons carbone tlscopique": [
                    "BN 04",
                ],
            },
            "PELLE": {
                "Mini Pelle  ARVA ": [
                    "PE 01",
                    "PE 02",
                    "PE 03",
                    "PE 04",
                    "PE 05",
                    "PE 06",
                    "PE 07",
                    "PE 08",
                    "PE 09",
                    "PE 10",
                    "PE 11",
                    "PE 12",
                    "PE 13",
                    "PE 14",
                    "PE 15",
                    "PE 16",
                    "PE 17",
                ],
                "Pelle  NICK IMPEX": [
                    "PE 18",
                    "PE 20",
                    "PE 21",
                ],
                "Pelle ": [
                    "PE 19",
                ],
                "Pelle BLACK ": [
                    "PE 22",
                    "PE 23",
                    "PE 24",
                    "PE 25",
                ],
                "Pelle  ARVA ": [
                    "PE 26",
                    "PE 27",
                    "PE 28",
                    "PE 29",
                    "PE 30",
                ],
            },
            "SONDE": {
                "Sondes Procable ": [
                    "SO 1",
                    "SO 2",
                    "SO 3",
                    "SO 4",
                    "SO 5",
                    "SO 8",
                    "SO 18",
                ],
                "Autre sonde ": [
                    "SO 19",
                    "SO 20",
                    "SO 21",
                    "SO 22",
                    "SO 24",
                    "SO 25",
                ],
                "SONDES non repr": [
                    "SO 27",
                ],
                "SONDES RECENTES": [
                    "SO 9",
                    "SO 10",
                ],
                "Sonde ARVA light 2,4": [
                    "SO 11",
                    "SO 13",
                    "SO 14",
                    "SO 15",
                    "SO 16",
                ],
            },
            "CRAMPONS": {
                "Crampons Vasak": [
                    "CR 01",
                    "CR 02",
                    "CR 03",
                    "CR 04",
                    "CR 05",
                    "CR 06",
                    "CR 07",
                    "CR 08",
                    "CR 09",
                    "CR 10",
                ],
                "Crampons Sarken": [
                    "CR 11",
                    "CR 12",
                    "CR 13",
                    "CR 14",
                    "CR 15",
                    "CR 16",
                    "CR 17",
                    "CR 18",
                    "CR 19",
                    "CR 20",
                ],
                "Crampons Grivel": [
                    "CR 21",
                    "CR 22",
                    "CR 23",
                    "CR 24",
                    "CR 25",
                    "CR 29",
                    "CR 32",
                    "CR 33",
                    "CR 34",
                ],
                "Crampons Grivel automatique": [
                    "CR 26",
                    "CR 27",
                    "CR 28",
                ],
                "Crampons CT climbing": [
                    "CR 30",
                    "CR 31",
                ],
            },
            "RAQUETTES NEIGE": {
                "Raquettes  neige classiques TSL 225": [
                    "RQ 09",
                    "RQ 46",
                    "RQ 19",
                    "RQ 22",
                    "RQ 44",
                    "RQ 12",
                    "RQ 45 ",
                ],
                "Raq  neige rapid fix  BALDAS": [
                    "RQ 41",
                    "RQ 10",
                    "RQ 42",
                    "RQ 40",
                ],
                "TSL 710": [
                    "RQ 14",
                ],
                "TSL identifi 9": [
                    "RQ 15",
                ],
                "": [
                    "RQ 51",
                ],
            },
            "RAQUETTES SURF": {
                "Raquettes MSR EVO surf ": [
                    "RS 01",
                    "RS 02",
                    "RS 03",
                    "RS 04",
                    "RS 05",
                    "RS 06",
                    "RS 07",
                ],
            },
        }
        for eType in equipmentsTypes.items():
            equipmentType = EquipmentType()
            equipmentType.name = eType[0]
            equipmentType.price = 5.5
            equipmentType.models = []
            for model in eType[1].items():
                equipmentModel = EquipmentModel()
                equipmentModel.name = model[0]
                equipmentModel.equipments = []
                for refEquipment in model[1]:
                    equipment = Equipment()
                    equipment.purchaseDate = datetime.datetime.now()
                    equipment.reference = refEquipment
                    equipment.purchasePrice = 15.50
                    equipmentModel.equipments.append(equipment)

                equipmentType.models.append(equipmentModel)
            db.session.add(equipmentType)
            db.session.commit()
