""" API for equipment.

"""
import json

from flask import url_for
from marshmallow import fields
from collectives.api.equipment import EquipmentSchema
from collectives.models.equipment import Equipment, EquipmentStatus

from collectives.models.reservation import Reservation, ReservationLine

from .common import blueprint, marshmallow


class ReservationSchema(marshmallow.Schema):
    """Schema to describe a reservation"""

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
    """API endpoint to list reservation.

    :return: A tuple:

        - JSON containing information describe in ReservationSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Reservation.query.all()

    data = ReservationSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


class ReservationLineSchema(marshmallow.Schema):
    """Schema to describe reservation line"""

    equipmentTypeName = fields.Function(lambda obj: obj.equipmentType.name)

    reservationLineURL = fields.Function(
        lambda obj: url_for(
            "reservation.view_reservationLine", reservationLine_id=obj.id
        )
    )

    class Meta:
        """Fields to expose"""

        fields = ("quantity", "equipmentTypeName", "reservationLineURL")


@blueprint.route("/reservation/<int:reservation_id>")
def reservation(reservation_id):
    """API endpoint to list reservation lines.

    :return: A tuple:

        - JSON containing information describe in ReservationLineSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Reservation.query.get(reservation_id).lines

    data = ReservationLineSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


@blueprint.route("/reservation/ligne/<int:line_id>")
def reservation_line(line_id):
    """API endpoint to list equipment in a reservation line.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = ReservationLine.query.get(line_id).equipments

    data = EquipmentSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


@blueprint.route("/reservation/autocomplete/<int:line_id>")
def autocomplete_availibles_equipments(line_id):
    """API endpoint to list equipment in a reservation line.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    type = ReservationLine.query.get(line_id).equipmentType

    query = type.get_all_equipments()
    
    data = EquipmentSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}