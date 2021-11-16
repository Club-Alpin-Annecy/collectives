""" API for equipement.

"""
import json

from flask import url_for
from marshmallow import fields

from collectives.models.equipment import EquipmentType


from .common import blueprint, marshmallow


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
    """Schema to describe activity types"""

    pathImg = fields.Function(photo_uri)
    urlEquipmentTypeDetail=fields.Function(lambda equipmentType: url_for("equipment.detail_equipment_type",typeId=equipmentType.id))
    class Meta:
        """Fields to expose"""
        fields = ("id", "name", "pathImg", "price", "deposit", "urlEquipmentTypeDetail")



@blueprint.route("/equipementType")
def equipemntType():
    query = EquipmentType.query.all()

    data = EquipmentTypeSchema(many=True).dump(query)

    print('-----------------------------------------------------------------------------------------------------------------------------------------------------')
    return json.dumps(data), 200, {"content-type": "application/json"}
