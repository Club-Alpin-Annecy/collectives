""" API for equipment.

"""
import json

from flask import url_for
from marshmallow import fields

from collectives.models.reservation import Reservation

from .common import blueprint, marshmallow


class ReservationSchema(marshmallow.Schema):
    """Schema to describe equipment"""

    # typeName = fields.Function(lambda obj: obj.model.equipmentType.name)
    # urlEquipmentTypeDetail = fields.Function(
    #     lambda obj: url_for(
    #         "equipment.detail_equipment_type", typeId=obj.model.equipmentType.id
    #     )
    # )
    userLicence = fields.Function(lambda obj: obj.user.license)
    statusName = fields.Function(lambda obj: obj.status.display_name())

    reservationURL = fields.Function(
        lambda obj: url_for("reservation.view_reservation", reservation_id=obj.id)
    )

    class Meta:
        """Fields to expose"""

        fields = (
            "collect_date",
            "return_date",
            "statusName",
            "userLicence",
            "reservationURL",
        )


@blueprint.route("/reservations")
def reservations():
    """API endpoint to list equipment.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Reservation.query.all()

    data = ReservationSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


class ReservationLineSchema(marshmallow.Schema):
    """Schema to describe equipment"""

    equipmentReference = fields.Function(lambda obj: obj.equipment.reference)

    equipmentURL = fields.Function(
        lambda obj: url_for("equipment.detail_equipment", equipment_id=obj.equipment.id)
    )

    class Meta:
        """Fields to expose"""

        fields = ("quantity", "equipmentReference", "equipmentURL")


@blueprint.route("/reservation/<int:reservation_id>")
def reservation(reservation_id):
    """API endpoint to list equipment.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Reservation.query.get(reservation_id).lines

    data = ReservationLineSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}
