""" API for equipment.

"""
import json

from flask import url_for, abort
from marshmallow import fields

from ..models import db, Equipment, EquipmentType, EquipmentModel


from .common import blueprint, marshmallow
from ..utils.numbers import format_currency


def photo_uri(equipment_type):
    """Generate an URI for event image using Flask-Images.

    Returned images are thumbnail of 200x130 px.

    :param event: Event which will be used to get the image.
    :type event: :py:class:`collectives.models.event.Event`
    :return: The URL to the thumbnail
    :rtype: string
    """
    if equipment_type.pathImg is not None:
        return url_for(
            "static", filename="uploads/typeEquipmentImg/" + equipment_type.pathImg
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

    """:type: string"""
    price = fields.Function(lambda equipmentType: format_currency(equipmentType.price))

    """:type: string"""
    deposit = fields.Function(
        lambda equipmentType: format_currency(equipmentType.deposit)
        if equipmentType.deposit
        else "-"
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


@blueprint.route("/equipmentType")
def equipment_types():
    """API endpoint to list equipment types.

    It can be filtered using tabulator filter and sorter.

    :return: A tuple:

        - JSON containing information describe in EquipmentTypeSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    query = EquipmentType.query.all()
    if query is not None:

        data = EquipmentTypeSchema(many=True).dump(query)
        return json.dumps(data), 200, {"content-type": "application/json"}

    return abort(404, "Equipment types not found")


class EquipmentModelSchema(marshmallow.Schema):
    """Schema to describe equipment model"""

    class Meta:
        """Fields to expose"""

        fields = ("id", "name", "manufacturer")


@blueprint.route("/modelsfromtype/<int:typeId>")
def equipment_model(type_id):
    """API endpoint to list equipment models.

    It can be filtered using tabulator filter and sorter.

    :return: A tuple:

        - JSON containing information describe in EquipmentModelSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    equipment_type = EquipmentType.query.get(type_id)
    if equipment_type is not None:
        models = equipment_type.models
        data = EquipmentModelSchema(many=True).dump(models)

        return json.dumps(data), 200, {"content-type": "application/json"}
    return abort(404, "Equipment type not found")


@blueprint.route(
    "/modelEdit/<int:model_id>/<string:name>/<string:manufacturer>", methods=["POST"]
)
def equipment_model_edit(model_id, name, manufacturer):
    """
    API endpoint to edit a model.

    :return: A tuple:

        - JSON containing information if OK
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    model = EquipmentModel.query.get(model_id)
    if model is not None:
        model.name = name
        model.manufacturer = manufacturer
        db.session.commit()
        return "{'response': 'OK'}", 200, {"content-type": "application/json"}

    return abort(404, "Equipment model not found")


@blueprint.route("/modelDelete/<int:model_id>", methods=["POST"])
def equipment_model_delete(model_id):
    """
    API endpoint to delete a model.

    :return: A tuple:

        - JSON containing information if OK
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    model = EquipmentModel.query.get(model_id)
    if model is not None:
        db.session.delete(model)
        db.session.commit()

        return "{'response': 'OK'}", 200, {"content-type": "application/json"}

    return abort(404, "Equipment model not found")


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
            "id",
            "reference",
            "modelName",
            "typeName",
            "statusName",
            "equipmentURL",
            "urlEquipmentTypeDetail",
        )


@blueprint.route("/equipment")
def equipment():
    """API endpoint to list equipment.

    It can be filtered using tabulator filter and sorter.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Equipment.query.all()
    if query is not None:
        data = EquipmentSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}
    return abort(404, "Equipment not found")
