""" Module for equipment related route

This modules contains the /equipment Blueprint
"""
import datetime
from flask import render_template, redirect, url_for, request
from flask import Blueprint


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


@blueprint.route("/", methods=["GET"])
def view_equipment():
    # equipments = Equipment.query.all()
    # equipments.commit()

    equipment = Equipment()
    equipment.purchaseDate = datetime.datetime.now()
    equipment.reference = "blabla"
    equipment.caution = 12.1
    equipment.purchasePrice = 15.50

    return render_template(
        "equipment/gestion/equipment.html",
        # equipments=equipments
        equipment=equipment,
    )


@blueprint.route("/equipment_type", methods=["GET", "POST"])
def view_equipment_type():

    listEquipmentType = EquipmentType.query.all()

    formAjout = EquipmentTypeForm()
    print(request)
    if formAjout.validate_on_submit():

        new_equipment_type = EquipmentType()

        new_equipment_type.name = formAjout.name.data
        new_equipment_type.price = float(formAjout.price.data)
        new_equipment_type.save_typeImg(formAjout.imageType_file.data)

        db.session.add(new_equipment_type)
        listEquipmentType.append(new_equipment_type)
        db.session.commit()
        return redirect(url_for(".view_equipment_type"))

    return render_template(
        "equipment/gestion/equipmentType/displayAll.html",
        # equipments=equipments
        # equipment=equipment,
        listEquipmentType=listEquipmentType,
        formAjout=formAjout,
    )


@blueprint.route("/equipment_type/<int:typeId>", methods=["GET", "POST"])
def detail_equipment_type(typeId):
    equipmentType = EquipmentType.query.get(typeId)
    formAjoutModel = EquipmentModelForm()
    formAjoutModel.equipment_type_id.data = typeId
    if formAjoutModel.validate_on_submit():
        new_equipment_model = EquipmentModel()
        new_equipment_model.name = formAjoutModel.name.data
        new_equipment_model.equipment_type_id = formAjoutModel.equipment_type_id.data
        db.session.add(new_equipment_model)
        db.session.commit()
        return redirect(url_for(".detail_equipment_type", typeId=typeId))

    formEdit = EquipmentTypeForm(obj=equipmentType)

    if formEdit.validate_on_submit():
        equipmentType.name = formEdit.name.data
        equipmentType.price = float(formEdit.price.data)
        equipmentType.save_typeImg(formEdit.imageType_file.data)
        db.session.commit()
        return redirect(url_for(".view_equipment_type"))

    return render_template(
        "equipment/gestion/equipmentType/displayDetail.html",
        equipmentType=equipmentType,
        formAjoutModel=formAjoutModel,
        formEdit=formEdit,
    )


@blueprint.route("/equipment_type/<int:typeId>/edit", methods=["GET", "POST"])
def edit_equipment_type(typeId):

    typeModified = EquipmentType.query.get(typeId)
    formEdit = EquipmentTypeForm(obj=typeModified)

    if formEdit.validate_on_submit():
        typeModified.name = formEdit.name.data
        typeModified.price = float(formEdit.price.data)
        typeModified.save_typeImg(formEdit.imageType_file.data)
        db.session.commit()
        return redirect(url_for(".view_equipment_type"))

    listEquipmentType = EquipmentType.query.all()
    formAjout = EquipmentTypeForm()

    return render_template(
        "equipment/gestion/equipmentType/displayAll.html",
        listEquipmentType=listEquipmentType,
        formAjout=formAjout,
        formEdit=formEdit,
        typeId=typeId,
    )


@blueprint.route(
    "/equipment_type/<int:typeId>/model<int:modelId>", methods=["GET", "POST"]
)
def edit_equipment_model(typeId, modelId):

    equipmentModelModified = EquipmentModel.query.get(modelId)
    formEditModel = EquipmentModelForm(obj=equipmentModelModified)

    if formEditModel.validate_on_submit():
        
        equipmentModelModified.name = formEditModel.name.data
        equipmentModelModified.equipment_type_id = formEditModel.equipmentType.data
        db.session.commit()
        return redirect(url_for(".detail_equipment_type", typeId=typeId))

    typeSelected = EquipmentType.query.get(typeId)
    formAjoutModel = EquipmentModelForm()
    listEquipmentModel = EquipmentModel.query.all()
    deleteFormModel = DeleteForm()
    return render_template(
        "equipment/gestion/equipmentType/displayDetail.html",
        listEquipmentModel=listEquipmentModel,
        formAjoutModel=formAjoutModel,
        equipmentType=typeSelected,
        formEditModel=formEditModel,
        modelId=modelId,
        deleteFormModel=deleteFormModel,
    )


@blueprint.route("/stock", methods=["GET", "POST"])
def view_equipment_stock():
    addEquipmentForm = EquipmentForm()

    if addEquipmentForm.validate_on_submit():
        new_equipment = Equipment()
        new_equipment.reference = addEquipmentForm.reference.data
        new_equipment.purchaseDate = addEquipmentForm.purchaseDate.data
        new_equipment.purchasePrice = addEquipmentForm.purchasePrice.data
        new_equipment.equipment_model_id = addEquipmentForm.equipment_model_id.data
        db.session.add(new_equipment)
        db.session.commit()
        return redirect(url_for(".view_equipment_stock"))

    equipmentTypeList = EquipmentType.query.all()

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/displayAll.html",
        equipmentTypeList=equipmentTypeList,
        addEquipmentForm=addEquipmentForm,
        deleteForm=deleteForm,
    )


@blueprint.route(
    "/stock/detail_equipment/<int:equipmentId>/edit", methods=["GET", "POST"]
)
def edit_equipment(equipmentId):
    equipmentModified = Equipment.query.get(equipmentId)
    editEquipmentForm = EquipmentForm(obj=equipmentModified)

    if editEquipmentForm.validate_on_submit():
        equipmentModified.reference = editEquipmentForm.reference.data
        equipmentModified.purchaseDate = editEquipmentForm.purchaseDate.data
        equipmentModified.purchasePrice = editEquipmentForm.purchasePrice.data
        equipmentModified.equipment_model_id = editEquipmentForm.equipment_model_id.data
        db.session.commit()
        return redirect(url_for(".detail_equipment", equipment_id=equipmentId))

    equipmentTypeList = EquipmentType.query.all()
    addEquipmentForm = EquipmentForm()
    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/displayAll.html",
        equipmentTypeList=equipmentTypeList,
        editEquipmentForm=editEquipmentForm,
        addEquipmentForm=addEquipmentForm,
        deleteForm=deleteForm,
        equipmentId=equipmentId,
    )


@blueprint.route("/stock/detail_equipment/<int:equipment_id>", methods=["GET", "POST"])
def detail_equipment(equipment_id):
    equipmentSelected = Equipment.query.get(equipment_id)

    editEquipmentForm = EquipmentForm(obj=equipmentSelected)

    if editEquipmentForm.validate_on_submit():
        equipmentSelected.reference = editEquipmentForm.reference.data
        equipmentSelected.purchaseDate = editEquipmentForm.purchaseDate.data
        equipmentSelected.purchasePrice = editEquipmentForm.purchasePrice.data
        equipmentSelected.equipment_model_id = editEquipmentForm.equipment_model_id.data
        db.session.commit()
        return redirect(url_for(".detail_equipment", equipment_id=equipment_id))

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/displayDetail.html",
        equipment=equipmentSelected,
        deleteForm=deleteForm,
        editEquipmentForm=editEquipmentForm,
    )


@blueprint.route("/delete_equipment/<int:equipmentId>", methods=["POST"])
def delete_equipment(equipmentId):
    del_equipment = Equipment.query.get(equipmentId)
    db.session.delete(del_equipment)
    return redirect(url_for(".view_equipment_stock"))


@blueprint.route("/delete_equipmentModel/<int:modelId>", methods=["POST"])
def delete_equipment_model(modelId):
    model = EquipmentModel.query.get(modelId)
    typeId = model.equipmentType.id
    db.session.delete(model)
    return redirect(url_for(".detail_equipment_type", typeId=typeId))


# @blueprint.route("/create_equipments_in_bdd", methods=["GET"])
def create_equipments_in_bdd():
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
            equipmentType.name = eType
            equipmentType.price = 5.5
            equipmentType.models = []
            for model in equipmentsTypes[eType]:
                equipmentModel = EquipmentModel()
                equipmentModel.name = model
                equipmentModel.equipments = []
                for refEquipment in equipmentsTypes[eType][model]:
                    equipment = Equipment()
                    equipment.purchaseDate = datetime.datetime.now()
                    equipment.reference = refEquipment
                    equipment.purchasePrice = 15.50
                    equipmentModel.equipments.append(equipment)

                equipmentType.models.append(equipmentModel)
            db.session.add(equipmentType)
            db.session.commit()
