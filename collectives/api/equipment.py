""" API for equipement.

"""
import json

from flask import url_for, request
from flask_login import current_user
from marshmallow import fields
from sqlalchemy import desc, and_

from collectives.models.equipment import Equipment, EquipmentType

from ..models import db, User, RoleIds, Role
from ..utils.access import valid_user, user_is, confidentiality_agreement

from .common import blueprint, marshmallow, avatar_url
from .event import ActivityTypeSchema


def photo_uri(equipmentType):
    """Generate an URI for event image using Flask-Images.

    Returned images are thumbnail of 200x130 px.

    :param event: Event which will be used to get the image.
    :type event: :py:class:`collectives.models.event.Event`
    :return: The URL to the thumbnail
    :rtype: string
    """
    if equipmentType.pathImg is not None:
        return url_for("static", filename="uploads/typeEquipmentImg/"+equipmentType.pathImg)
    return url_for("static", filename="img/icon/ionicon/md-images.svg")

def equipmentType_uri(equipmentType):
    
    return url_for("equipment.detail_equipment_type",typeId=equipmentType.id)

class EquipmentTypeSchema(marshmallow.Schema):
    """Schema to describe equipment types"""

    pathImg = fields.Function(photo_uri)
    urlEquipmentTypeDetail=fields.Function(
        lambda equipmentType: url_for("equipment.detail_equipment_type",typeId=equipmentType.id)
    )
    
    class Meta:
        """Fields to expose"""

        fields = ("id", "name", "pathImg", "price", "deposit", "urlEquipmentTypeDetail")

@blueprint.route("/equipementType")
def equipemntType():
   

    query = EquipmentType.query.all()

    data = EquipmentTypeSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


def getModelNameFromAnEquipment(equipment):
    return equipment.model.name

def getAnEquipemtnTypeNameFromAnEquipment(equipment):
    return equipment.model.equipmentType.name

class EquipmentSchema(marshmallow.Schema):
    """Schema to describe equipment"""
    typeName=fields.Function(lambda obj: obj.model.equipmentType.name)
    urlEquipmentTypeDetail=fields.Function(lambda obj: 
        url_for("equipment.detail_equipment_type",
            typeId=obj.model.equipmentType.id
        )
    )
    modelName = fields.Function(lambda obj: obj.model.name)
    statusName = fields.Function(lambda obj: obj.status.display_name())

    equipmentURL=fields.Function(lambda obj: 
        url_for("equipment.detail_equipment",
            equipment_id=obj.id
        )
    )


    class Meta:
        """Fields to expose"""

        fields = (
            "reference", 
            "modelName", 
            "typeName", 
            "statusName",
            "equipmentURL", 
            "urlEquipmentTypeDetail"
        )


@blueprint.route("/equipement")
def equipemnt():
   

    query = Equipment.query.all()

    data = EquipmentSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}
