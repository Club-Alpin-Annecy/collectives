""" API for equipment.

"""
import json

from flask import url_for
from marshmallow import fields

from collectives.models.equipment import Equipment, EquipmentType, EquipmentModel


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
        return url_for(
            "static", filename="uploads/typeEquipmentImg/" + equipmentType.pathImg
        )
    return url_for("static", filename="img/icon/ionicon/md-images.svg")


class EquipmentTypeSchema(marshmallow.Schema):
    """Schema to describe equipment types"""

    pathImg = fields.Function(photo_uri)
    urlEquipmentTypeDetail = fields.Function(
        lambda equipmentType: url_for(
            "equipment.detail_equipment_type", typeId=equipmentType.id
        )
    )
    """:type: int"""
    nbTotal = fields.Function(lambda equipmentType: equipmentType.nb_total())

    """:type: int"""
    nbTotalUnavailable = fields.Function(
        lambda equipmentType: equipmentType.nb_total_unavailable()
    )

    """:type: int"""
    nbTotalAvailable = fields.Function(
        lambda equipmentType: equipmentType.nb_total_available()
    )

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "name",
            "pathImg",
            "price",
            "deposit",
            "urlEquipmentTypeDetail",
            "nbTotal",
            "nbTotalUnavailable",
            "nbTotalAvailable",
        )


class EquipmentModelSchema(marshmallow.Schema):
    """Schema to describe equipemnt model"""

    class Meta:
        """Fields to expose"""

        fields = ("id", "name")


@blueprint.route("/equipmentType")
def equipemntType():
    """API endpoint to list equipment types.

    It can be filtered using tabulator filter and sorter.

    :return: A tuple:

        - JSON containing information describe in EquipmentTypeSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    query = EquipmentType.query.all()

    data = EquipmentTypeSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


class EquipmentSchema(marshmallow.Schema):
    """Schema to describe equipment"""

    typeName = fields.Function(lambda obj: obj.model.equipmentType.name)
    urlEquipmentTypeDetail = fields.Function(
        lambda obj: url_for(
            "equipment.detail_equipment_type", typeId=obj.model.equipmentType.id
        )
    )
    modelName = fields.Function(lambda obj: obj.model.name)
    statusName = fields.Function(lambda obj: obj.status.display_name())

    equipmentURL = fields.Function(
        lambda obj: url_for("equipment.detail_equipment", equipment_id=obj.id)
    )

    class Meta:
        """Fields to expose"""

        fields = (
            "reference",
            "modelName",
            "typeName",
            "statusName",
            "equipmentURL",
            "urlEquipmentTypeDetail",
        )


@blueprint.route("/equipment")
def equipemnt():
    """API endpoint to list equipment.

    It can be filtered using tabulator filter and sorter.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Equipment.query.all()

    data = EquipmentSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


@blueprint.route("/modelsfromtype/<int:typeId>")
def equipemntModel(typeId):
    """API endpoint to list equipment models.

    It can be filtered using tabulator filter and sorter.

    :return: A tuple:

        - JSON containing information describe in EquipmentModelSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = EquipmentModel.query.all()
    query = EquipmentType.query.get(typeId).models

    data = EquipmentModelSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}
