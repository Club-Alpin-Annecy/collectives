""" Module for equipment related route

This modules contains the /equipment Blueprint
"""
from flask import flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint, escape
from flask_login import current_user

from flask_uploads import UploadSet, IMAGES

from ..forms.equipment import AddEquipmentTypeForm, DeleteForm, EquipmentModelForm,EquipmentForm

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
        "equipment/gestion/equipment.html",
        # equipments=equipments
        equipment=equipment,
    )




@blueprint.route("/equipment_type", methods=["GET", "POST"])
def view_equipment_type():
    
    listEquipementType = EquipmentType.query.all()

    formAjout = AddEquipmentTypeForm()
    print(request)
    if formAjout.validate_on_submit():

        new_equipment_type = EquipmentType()

        new_equipment_type.name = formAjout.name.data
        new_equipment_type.price = float(formAjout.price.data)
        new_equipment_type.save_typeImg(formAjout.imageType_file.data)


        db.session.add(new_equipment_type)
        listEquipementType.append(new_equipment_type)
        db.session.commit()


    return render_template(
        "equipment/gestion/equipmentType/displayAll.html",
        # equipments=equipments
        # equipment=equipment,
        listEquipementType=listEquipementType,
        formAjout=formAjout
    )

@blueprint.route("/equipment_type/edit<int:typeId>", methods=["GET", "POST"])
def edit_equipment_type(typeId):

    
    typeModified = EquipmentType.query.get(typeId)
    formEdit = AddEquipmentTypeForm(obj=typeModified)
    
    if formEdit.validate_on_submit():

        typeModified.name = formEdit.name.data
        typeModified.price = float(formEdit.price.data)
        typeModified.save_typeImg(formEdit.imageType_file.data)
        db.session.commit()
        
        return redirect(url_for(".view_equipment_type"))

    listEquipementType = EquipmentType.query.all()
    formAjout = AddEquipmentTypeForm()

    return render_template(
        "equipment/gestion/equipmentType/displayAll.html",
        # equipments=equipments
        # equipment=equipment,
        listEquipementType=listEquipementType,
        formAjout=formAjout,
        formEdit=formEdit,
        typeId=typeId,
    )


@blueprint.route("/equipment_models", methods=["GET", "POST"])
@blueprint.route("/equipment_models/edit<int:modelId>", methods=["GET", "POST"])
def crud_equipment_model(modelId = None):

    formAjout = EquipmentModelForm()
    
    formEdit = None
    if(modelId is not None):
        equipmentModified = EquipmentModel.query.get(modelId)
        formEdit = EquipmentModelForm(obj=EquipmentModel.query.get(modelId))

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
        formAjout.name.data = ""
        formAjout.equipmentType.data= ""

    listEquipementModel = EquipmentModel.query.all()
    deleteForm = DeleteForm()
    return render_template(
        "equipment/gestion/equipmentModel/displayAll.html",
        listEquipementModel=listEquipementModel,
        formAjout=formAjout,
        formEdit=formEdit,
        modelId=modelId,
        deleteForm=deleteForm

    )




@blueprint.route("/stock", methods=["GET", "POST"])
def view_equipment_stock():
    addEquipmentForm = EquipmentForm()

    if addEquipmentForm.validate_on_submit():
        new_equipment = Equipment()
        new_equipment.reference = addEquipmentForm.reference.data
        new_equipment.purchaseDate = addEquipmentForm.purchaseDate.data
        new_equipment.purchasePrice = addEquipmentForm.purchasePrice.data
        new_equipment.model = addEquipmentForm.model.data
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

@blueprint.route("/stock/<int:equipmentId>/edit", methods=["GET", "POST"])
def edit_equipment(equipmentId):
    equipmentModified = Equipment.query.get(equipmentId)
    editEquipmentForm = EquipmentForm(obj=equipmentModified)
    

    if editEquipmentForm.validate_on_submit():
        equipmentModified.reference = editEquipmentForm.reference.data
        equipmentModified.purchaseDate = editEquipmentForm.purchaseDate.data
        equipmentModified.purchasePrice = editEquipmentForm.purchasePrice.data
        equipmentModified.model = editEquipmentForm.model.data
        db.session.commit()
        return redirect(url_for(".view_equipment_stock"))
        
    equipmentTypeList = EquipmentType.query.all()
    addEquipmentForm = EquipmentForm()
    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/displayAll.html",
        equipmentTypeList=equipmentTypeList,
        editEquipmentForm=editEquipmentForm,
        addEquipmentForm=addEquipmentForm,
        deleteForm=deleteForm,
        equipmentId=equipmentId
    )


@blueprint.route("/stock/detail_equipment/<int:equipment_id>", methods=["GET", "POST"])
def detail_equipment(equipment_id):
    equipmentSelected = Equipment.query.get(equipment_id)

    print(equipmentSelected)
    deleteForm = DeleteForm()

    return render_template(
        "equipment/gestion/equipment/displayDetail.html",
        equipment = equipmentSelected,
        deleteForm=deleteForm,
    )


@blueprint.route("/delete_equipment/<int:equipmentId>", methods=["POST"])
def delete_equipment(equipmentId):
    del_equipment = Equipment.query.get(equipmentId)
    db.session.delete(del_equipment)
    return redirect(url_for(".view_equipment_stock"))


@blueprint.route("/delete_equipmentModel/<int:modelId>", methods=["POST"])
def delete_equipment_model(modelId):
    model = EquipmentModel.query.get(modelId)
    db.session.delete(model)
    return redirect(url_for(".crud_equipment_model"))




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
