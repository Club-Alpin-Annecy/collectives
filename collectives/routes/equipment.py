""" Module for equipment related route

This modules contains the /equipment Blueprint
"""
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
        new_equipment_type.deposit = float(addingFrom.deposit.data)
        new_equipment_type.save_typeImg(addingFrom.imageType_file.data)

        db.session.add(new_equipment_type)
        db.session.commit()
        return redirect(url_for(".display_all_type"))

    list_equipmentt_type = EquipmentType.query.all()

    return render_template(
        "equipment/gestion/equipmentType/equipment_types.html",
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
        new_equipment_model.manufacturer = adding_from_model.manufacturer.data
        new_equipment_model.equipment_type_id = typeId
        db.session.add(new_equipment_model)
        db.session.commit()
        return redirect(url_for(".detail_equipment_type", typeId=typeId))

    equipmentType = EquipmentType.query.get(typeId)
    formEdit = EquipmentTypeForm(obj=equipmentType)

    if formEdit.validate_on_submit():
        equipmentType.name = formEdit.name.data
        equipmentType.price = float(formEdit.price.data)
        equipmentType.deposit = float(formEdit.deposit.data)
        equipmentType.save_typeImg(formEdit.imageType_file.data)
        db.session.commit()
        return redirect(url_for(".display_all_type"))

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipmentType/equipment_type.html",
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
        typeModified.deposit = float(formEdit.deposit.data)
        typeModified.save_typeImg(formEdit.imageType_file.data)
        db.session.commit()
        return redirect(url_for(".display_all_type"))

    list_equipmentt_type = EquipmentType.query.all()
    addingFrom = EquipmentTypeForm()

    return render_template(
        "equipment/gestion/equipmentType/equipment_types.html",
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
        equipmentModelModified.manufacturer = formEditModel.manufacturer.data
        equipmentModelModified.equipment_type_id = formEditModel.equipmentType.data
        db.session.commit()
        return redirect(url_for(".detail_equipment_type", typeId=typeId))

    typeSelected = EquipmentType.query.get(typeId)
    adding_from_model = EquipmentModelForm()
    listEquipmentModel = EquipmentModel.query.all()
    deleteFormModel = DeleteForm()
    return render_template(
        "equipment/gestion/equipmentType/equipment_type.html",
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
        new_equipment.serial_number = addEquipmentForm.serial_number.data
        new_equipment.purchasePrice = addEquipmentForm.purchasePrice.data
        new_equipment.equipment_model_id = addEquipmentForm.equipment_model_id.data
        db.session.add(new_equipment)
        db.session.commit()
        return redirect(url_for(".stock_situation_stock"))

    equipmentTypeList = EquipmentType.query.all()

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/equipments.html",
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
        equipmentSelected.serial_number = editEquipmentForm.serial_number.data
        equipmentSelected.purchaseDate = editEquipmentForm.purchaseDate.data
        equipmentSelected.purchasePrice = editEquipmentForm.purchasePrice.data
        equipmentSelected.equipment_model_id = editEquipmentForm.equipment_model_id.data
        db.session.commit()
        return redirect(url_for(".detail_equipment", equipment_id=equipment_id))

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/equipment.html",
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
