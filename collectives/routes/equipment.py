""" Module for equipment related route

This modules contains the /equipment Blueprint
"""
from flask import flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint, escape
from flask_login import current_user


from ..forms.equipment import AddEquipmentTypeForm, DeleteEquipmentForm, AddEquipmentModelForm

import datetime

from ..models import db, User, Equipment, EquipmentType, EquipmentModel

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
        "equipment/equipment.html",
        # equipments=equipments
        equipment=equipment,
    )




@blueprint.route("/equipment_type", methods=["GET", "POST"])
def view_equipment_type():
    
    listEquipementType = EquipmentType.query.all()

    form = AddEquipmentTypeForm()

    if form.validate_on_submit():

        new_equipment_type = EquipmentType()

        new_equipment_type.name = form.libelleEquipmentType.data
        new_equipment_type.price = float(form.priceEquipmentType.data)


        db.session.add(new_equipment_type)
        listEquipementType.append(new_equipment_type)
        db.session.commit()


    return render_template(
        "equipment/equipment_type.html",
        # equipments=equipments
        # equipment=equipment,
        listEquipementType=listEquipementType,
        form=form

    )

@blueprint.route("/equipment_models", methods=["GET", "POST"])
@blueprint.route("/equipment_models/edit<int:modelId>", methods=["GET", "POST"])
def crud_equipment_model(modelId = None):

    formAjout = AddEquipmentModelForm()
    formEdit = None
    if(modelId is not None):
        equipmentModified = EquipmentModel.query.get(modelId)
        formEdit = AddEquipmentModelForm(obj=EquipmentModel.query.get(modelId))

        if formEdit.validate_on_submit():
            equipmentModified.name = formEdit.name.data
            equipmentModified.equipmentType = formEdit.equipmentType.data
            db.session.commit()
            return redirect(url_for(".crud_equipment_model"))


    elif formAjout.validate_on_submit():
        new_equipment_model = EquipmentModel()
        new_equipment_model.name = formAjout.name.data
        new_equipment_model.equipmentType = formAjout.equipmentType.data
        db.session.add(new_equipment_model)
        db.session.commit()

    


    listEquipementModel = EquipmentModel.query.all()

    return render_template(
        "equipment/equipment_model.html",
        listEquipementModel=listEquipementModel,
        formAjout=formAjout,
        formEdit=formEdit,
        modelId=modelId

    )



@blueprint.route("/stock", methods=["GET"])
def view_equipment_stock():
    # equipments = Equipment.query.all()
    # equipments.commit()


    equipmentTypeList = EquipmentType.query.all()

    form = DeleteEquipmentForm()

    return render_template(
        "equipment/equipment_stock.html",
        # equipments=equipments
        equipmentTypeList=equipmentTypeList,
        form=form,
    )


@blueprint.route("/delete/<int:equipment_id>", methods=["POST"])
def delete_equipment(equipment_id):
    del_equipment = Equipment.query.get(equipment_id)
    db.session.delete(del_equipment)
    return redirect(url_for(".view_equipment_stock"))





#@blueprint.route("/create_equipments_in_bdd", methods=["GET"])
def create_equipments_in_bdd():
    if(EquipmentType.query.all() == []):
        equipmentsTypesNames = ['Piolet', 'Crampon', 'DVA', 'Corde a sauter']

        equipmentTypeList = []
        for i, name in enumerate(equipmentsTypesNames):
            equipmentType = EquipmentType()
            equipmentType.name = name
            equipmentType.price = i+5.5
            equipmentType.models = []
            for y in range(0,4):
                equipmentModel = EquipmentModel()
                equipmentModel.name = "model "+str(i)+str(y)
                equipmentModel.equipments = []
                for z in range(0,4):
                    equipment = Equipment()
                    equipment.purchaseDate = datetime.datetime.now()
                    equipment.reference = "REF"+str(i)+str(y)+str(z)
                    equipment.purchasePrice = 15.50
                    equipmentModel.equipments.append(equipment)

                equipmentType.models.append(equipmentModel)
            equipmentTypeList.append(equipmentType) 
            db.session.add(equipmentTypeList[i])
            db.session.commit()
