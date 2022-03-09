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

    list_equipment_type = EquipmentType.query.all()

    return render_template(
        "equipment/gestion/equipmentType/equipment_types.html",
        list_equipmentt_type=list_equipment_type,
    )


@blueprint.route("/equipment_type/<int:typeId>", methods=["GET", "POST"])
def detail_equipment_type(typeId):
    """
    Show one equipment type and its models
    """
    adding_from_model = EquipmentModelForm()
    if adding_from_model.validate_on_submit():
        new_model = EquipmentModel()
        adding_from_model.populate_obj(new_model)
        new_model.equipment_type_id = typeId
        db.session.add(new_model)
        db.session.commit()
        return redirect(url_for(".detail_equipment_type", typeId=typeId))

    equipmentType = EquipmentType.query.get(typeId)
    formEdit = EquipmentTypeForm(obj=equipmentType)

    if formEdit.validate_on_submit():
        formEdit.populate_obj(equipmentType)
        equipmentType.save_typeImg(formEdit.imageType_file.data)
        db.session.commit()
        return redirect(url_for(".detail_equipment_type", typeId=typeId))

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipmentType/equipment_type.html",
        equipmentType=equipmentType,
        adding_from_model=adding_from_model,
        formEdit=formEdit,
        deleteForm=deleteForm,
    )


@blueprint.route("/equipment_type/add", methods=["GET", "POST"])
def add_equipment_type():
    """
    Route to add an equipment type
    """
    title = "Ajouter un type d'équipement"
    addingFrom = EquipmentTypeForm()
    if addingFrom.validate_on_submit():
        new_equipment_type = EquipmentType()
        addingFrom.populate_obj(new_equipment_type)
        new_equipment_type.save_typeImg(addingFrom.imageType_file.data)
        db.session.add(new_equipment_type)
        db.session.commit()
        return redirect(url_for(".display_all_type"))

    return render_template(
        "equipment/gestion/equipmentType/add_equipment_type.html",
        form=addingFrom,
        title=title,
    )


@blueprint.route("/delete_equipmentType/<int:equipmentTypeId>", methods=["POST"])
def delete_equipment_type(equipmentTypeId):
    """Route to delete a specific type"""
    equipmentType = EquipmentType.query.get(equipmentTypeId)
    db.session.delete(equipmentType)
    db.session.commit()
    return redirect(url_for(".stock_situation"))


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

    equipmentTypeList = EquipmentType.query.all()

    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/equipments.html",
        equipmentTypeList=equipmentTypeList,
        deleteForm=deleteForm,
    )


@blueprint.route("/stock/add", methods=["GET", "POST"])
def add_equipment():
    """
    Route to add an equipment
    """

    if not current_user.matching_roles(
        [RoleIds.EquipmentManager, RoleIds.Administrator]
    ):
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    title = "Ajouter un équipement"
    addEquipmentForm = EquipmentForm()
    e_model = EquipmentModel.query.get(addEquipmentForm.equipment_model_id.data)

    # Recalculating the new reference
    if e_model is not None:
        e_type = EquipmentType.query.get(e_model.equipment_type_id)
        addEquipmentForm.reference.data = e_type.get_new_reference()
    else:
        addEquipmentForm.reference.data = None

    has_changed_model = addEquipmentForm.update_model.data
    # If has_changed_model is True, this is only a change of model, not a real submit
    if not has_changed_model and addEquipmentForm.validate_on_submit():
        new_equipment = Equipment()
        addEquipmentForm.populate_obj(new_equipment)
        db.session.add(new_equipment)
        db.session.commit()
        return redirect(url_for(".stock_situation_stock"))

    return render_template(
        "equipment/gestion/equipment/add_equipment.html",
        form=addEquipmentForm,
        title=title,
    )


@blueprint.route("/stock/detail_equipment/<int:equipment_id>", methods=["GET", "POST"])
def detail_equipment(equipment_id):
    """
    Show the detail af an equipment and a form to edit it
    """
    equipmentSelected = Equipment.query.get(equipment_id)

    editEquipmentForm = EquipmentForm(obj=equipmentSelected)

    if editEquipmentForm.validate_on_submit():
        editEquipmentForm.populate_obj(equipmentSelected)
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
    db.session.commit()
    return redirect(url_for(".stock_situation_stock"))
