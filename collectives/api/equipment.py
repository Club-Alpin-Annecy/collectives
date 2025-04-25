"""API for equipment."""

import json

from flask import url_for, abort
from marshmallow import fields

from collectives.api.common import blueprint, marshmallow
from collectives.models import db, Equipment, EquipmentType, EquipmentModel
from collectives.utils.numbers import format_currency


def photo_uri(equipment_type):
    """Generate an URI for event image using Flask-Images.

    Returned images are thumbnail of 200x130 px.

    :param event: Event which will be used to get the image.
    :type event: :py:class:`collectives.models.event.Event`
    :return: The URL to the thumbnail
    :rtype: string
    """
    if equipment_type.path_img is not None:
        return url_for(
            "static", filename="uploads/typeEquipmentImg/" + equipment_type.path_img
        )
    return url_for("static", filename="img/icon/ionicon/md-images.svg")


class EquipmentTypeSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema to describe equipment types"""

    path_img = fields.Function(photo_uri)
    url_equipment_type_detail = fields.Function(
        lambda equipment_type: url_for(
            "equipment.detail_equipment_type", type_id=equipment_type.id
        )
    )
    """:type: int"""
    nb_total = fields.Function(lambda equipment_type: equipment_type.nb_total())

    """:type: int"""
    nb_total_unavailable = fields.Function(
        lambda equipment_type: equipment_type.nb_total_unavailable()
    )

    """:type: int"""
    nb_total_available = fields.Function(
        lambda equipment_type: equipment_type.nb_total_available()
    )

    """:type: string"""
    price = fields.Function(
        lambda equipment_type: format_currency(equipment_type.price)
    )

    """:type: string"""
    deposit = fields.Function(
        lambda equipment_type: (
            format_currency(equipment_type.deposit) if equipment_type.deposit else "-"
        )
    )

    class Meta:
        """Fields to expose"""

        model = EquipmentType
        fields = (
            "id",
            "name",
            "path_img",
            "price",
            "deposit",
            "url_equipment_type_detail",
            "nb_total",
            "nb_total_unavailable",
            "nb_total_available",
        )


@blueprint.route("/equipment_type")
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


class EquipmentModelSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema to describe equipment model"""

    class Meta:
        """Fields to expose"""

        model = EquipmentModel
        fields = ("id", "name", "manufacturer")


@blueprint.route("/modelsfromtype/<int:type_id>")
def equipment_model(type_id):
    """API endpoint to list equipment models.

    It can be filtered using tabulator filter and sorter.

    :return: A tuple:

        - JSON containing information describe in EquipmentModelSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    equipment_type = db.session.get(EquipmentType, type_id)
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
    model = db.session.get(EquipmentModel, model_id)
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
    model = db.session.get(EquipmentModel, model_id)
    if model is not None:
        db.session.delete(model)
        db.session.commit()

        return "{'response': 'OK'}", 200, {"content-type": "application/json"}

    return abort(404, "Equipment model not found")


class EquipmentSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema to describe equipment"""

    type_name = fields.Function(lambda obj: obj.model.equipment_type.name)
    url_equipment_type_detail = fields.Function(
        lambda obj: url_for(
            "equipment.detail_equipment_type", type_id=obj.model.equipment_type.id
        )
    )
    model_name = fields.Function(lambda obj: obj.model.name)
    status_name = fields.Function(lambda obj: obj.status.display_name())

    equipment_url = fields.Function(
        lambda obj: url_for("equipment.detail_equipment", equipment_id=obj.id)
    )

    class Meta:
        """Fields to expose"""

        model = Equipment
        fields = (
            "id",
            "reference",
            "model_name",
            "type_name",
            "status_name",
            "equipment_url",
            "url_equipment_type_detail",
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
