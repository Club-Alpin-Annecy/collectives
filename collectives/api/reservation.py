""" API for equipment.

"""
import json

from flask import url_for
from marshmallow import fields
from collectives.models.equipment import Equipment, EquipmentStatus
from collectives.api.equipment import EquipmentSchema, EquipmentSchema

from collectives.models.reservation import Reservation, ReservationLine

from ..models import db


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


@blueprint.route("/reservation/lignerented/<int:line_id>")
def reservation_line_equipments_rented(line_id):
    """API endpoint to list equipment rented in a reservation line.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    query = ReservationLine.query.get(line_id).get_equipments_rented()

    data = EquipmentSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


@blueprint.route("/reservation/lignereturned/<int:line_id>")
def reservation_line_equipments_returned(line_id):
    """API endpoint to list equipment rented in a reservation line.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    query = ReservationLine.query.get(line_id).get_equipments_returned()

    data = EquipmentSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


@blueprint.route("/reservation/autocomplete/<int:line_id>")
def autocomplete_availables_equipments(line_id):
    """API endpoint to list equipment in a reservation line.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    eType = ReservationLine.query.get(line_id).equipmentType

    query = eType.get_all_equipments_availables()
    data = EquipmentSchema(many=True).dump(query)

    return json.dumps(data), 200, {"content-type": "application/json"}


@blueprint.route(
    "/set_available_equipment/<int:equipment_id>",
    methods=["POST"],
)
def set_available_equipment(equipment_id):
    """
    API endpoint to remove an equipment from a réservation.

    :return: A tuple:

        - JSON containing information if OK
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    equipment = Equipment.query.get(equipment_id)

    equipment.status = EquipmentStatus.Available
    db.session.commit()

    return (
        "{'response': 'Status changed OK'}",
        200,
        {"content-type": "application/json"},
    )


@blueprint.route(
    "/remove_reservationLine_equipment/<int:equipment_id>/<int:line_id>",
    methods=["POST"],
)
def remove_reservationLine_equipment(equipment_id, line_id):
    """
    API endpoint to remove an equipment from a réservation.

    :return: A tuple:

        - JSON containing information if OK
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    line = ReservationLine.query.get(line_id)
    equipment = Equipment.query.get(equipment_id)
    line.equipments.remove(equipment)
    equipment.status = EquipmentStatus.Available
    db.session.commit()

    return (
        "{'response': 'Status changed OK'}",
        200,
        {"content-type": "application/json"},
    )
