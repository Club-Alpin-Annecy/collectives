""" Module for equipment related route

This modules contains the /equipment Blueprint
"""

from flask_login import current_user
from flask import render_template, redirect, url_for
from flask import Blueprint, flash

from collectives.forms.equipment import EquipmentTypeForm, DeleteForm
from collectives.forms.equipment import EquipmentModelForm
from collectives.forms.equipment import EquipmentForm
from collectives.models import db, Equipment, EquipmentType, EquipmentModel, RoleIds
from collectives.utils.access import valid_user, confidentiality_agreement, user_is


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
    - check if user has signed the confidentiality agreement
      :py:func:`collectives.utils.access.confidentiality_agreement`
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


@blueprint.route("/equipment_type", methods=["GET", "POST"])
def display_all_type():
    """
    Show all the equipment types and a form for to add one
    """

    list_equipment_type = EquipmentType.query.all()

    return render_template(
        "equipment/gestion/equipment_type/equipment_types.html",
        list_equipmentt_type=list_equipment_type,
    )


@blueprint.route("/equipment_type/<int:type_id>", methods=["GET", "POST"])
def detail_equipment_type(type_id):
    """
    Show one equipment type and its models
    """
    adding_from_model = EquipmentModelForm()
    equipment_type = db.session.get(EquipmentType, type_id)
    form_edit = EquipmentTypeForm(obj=equipment_type)

    if form_edit.validate_on_submit():
        form_edit.populate_obj(equipment_type)
        equipment_type.save_type_img(form_edit.imageType_file.data)
        db.session.commit()
        return redirect(url_for(".detail_equipment_type", type_id=type_id))

    delete_form = DeleteForm()

    return render_template(
        "equipment/gestion/equipment_type/equipment_type.html",
        equipment_type=equipment_type,
        adding_from_model=adding_from_model,
        formEdit=form_edit,
        delete_form=delete_form,
    )


@blueprint.route("/equipment_type/<int:type_id>/add", methods=["GET", "POST"])
def add_equipment_model(type_id):
    """
    Route to add an equipment model
    """
    adding_from_model = EquipmentModelForm()
    if adding_from_model.validate_on_submit():
        new_model = EquipmentModel()
        adding_from_model.populate_obj(new_model)
        new_model.equipment_type_id = type_id
        db.session.add(new_model)
        db.session.commit()
    return redirect(url_for(".detail_equipment_type", type_id=type_id))


@blueprint.route("/equipment_type/add", methods=["GET", "POST"])
def add_equipment_type():
    """
    Route to add an equipment type
    """
    title = "Ajouter un type d'équipement"
    adding_from = EquipmentTypeForm()
    if adding_from.validate_on_submit():
        new_equipment_type = EquipmentType()
        adding_from.populate_obj(new_equipment_type)
        new_equipment_type.save_type_img(adding_from.imageType_file.data)
        db.session.add(new_equipment_type)
        db.session.commit()
        return redirect(url_for(".display_all_type"))

    return render_template(
        "equipment/gestion/equipment_type/add_equipment_type.html",
        form=adding_from,
        title=title,
    )


@blueprint.route("/delete_equipment_type/<int:equipment_type_id>", methods=["POST"])
def delete_equipment_type(equipment_type_id):
    """Route to delete a specific type"""
    equipment_type = db.session.get(EquipmentType, equipment_type_id)
    db.session.delete(equipment_type)
    db.session.commit()
    return redirect(url_for(".stock_situation"))


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

    equipment_type_list = EquipmentType.query.all()

    delete_form = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/equipments.html",
        equipment_type_list=equipment_type_list,
        delete_form=delete_form,
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
    add_equipment_form = EquipmentForm()
    e_model = db.session.get(EquipmentModel, add_equipment_form.equipment_model_id.data)

    # Recalculating the new reference
    if e_model is not None:
        e_type = db.session.get(EquipmentType, e_model.equipment_type_id)
        add_equipment_form.reference.data = e_type.get_new_reference()
    else:
        add_equipment_form.reference.data = None

    has_changed_model = add_equipment_form.update_model.data
    # If has_changed_model is True, this is only a change of model, not a real submit
    if not has_changed_model and add_equipment_form.validate_on_submit():
        new_equipment = Equipment()
        add_equipment_form.populate_obj(new_equipment)
        db.session.add(new_equipment)
        db.session.commit()
        new_equipment.get_type().increment_last_reference()
        db.session.commit()
        return redirect(url_for(".stock_situation_stock"))

    return render_template(
        "equipment/gestion/equipment/add_equipment.html",
        form=add_equipment_form,
        title=title,
    )


@blueprint.route("/stock/detail_equipment/<int:equipment_id>", methods=["GET", "POST"])
def detail_equipment(equipment_id):
    """
    Show the detail af an equipment and a form to edit it
    """
    selected_equipment = db.session.get(Equipment, equipment_id)

    edit_equipment_form = EquipmentForm(obj=selected_equipment)

    if edit_equipment_form.validate_on_submit():
        edit_equipment_form.populate_obj(selected_equipment)
        db.session.commit()
        return redirect(url_for(".detail_equipment", equipment_id=equipment_id))

    delete_form = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/equipment.html",
        equipment=selected_equipment,
        delete_form=delete_form,
        editEquipmentForm=edit_equipment_form,
    )


@blueprint.route("/delete_equipment/<int:equipment_id>", methods=["POST"])
def delete_equipment(equipment_id):
    """
    Route to delete a specific equipment
    """
    del_equipment = db.session.get(Equipment, equipment_id)
    db.session.delete(del_equipment)
    db.session.commit()
    return redirect(url_for(".stock_situation_stock"))
