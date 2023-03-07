""" API for reservation.

"""
from datetime import datetime, timedelta
import json

from flask_login import current_user
from flask import url_for, request, abort
from marshmallow import fields
from sqlalchemy.sql import text

from collectives.api.common import blueprint, marshmallow
from collectives.api.equipment import EquipmentSchema
from collectives.models import db, Equipment, EquipmentStatus, Reservation
from collectives.models import ReservationLine, ReservationStatus, User


class ReservationSchema(marshmallow.Schema):
    """Schema to describe a reservation"""

    user_licence = fields.Function(lambda obj: obj.user.license if obj.user else "")
    status_name = fields.Function(lambda obj: obj.status.display_name())
    user_full_name = fields.Function(lambda obj: obj.user.full_name())
    reservation_url = fields.Function(
        lambda obj: url_for("reservation.view_reservation", reservation_id=obj.id)
    )

    reservation_url_user = fields.Function(
        lambda obj: url_for("reservation.my_reservation", reservation_id=obj.id)
    )

    class Meta:
        """Fields to expose"""

        fields = (
            "collect_date",
            "return_date",
            "status_name",
            "user_licence",
            "reservation_url",
            "reservation_url_user",
            "user_full_name",
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

    if query is not None:
        data = ReservationSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}

    return abort(404, "Reservations not found")


@blueprint.route("/reservations_of_day")
def reservations_of_day():
    """API endpoint to list reservation.

    :return: A tuple:

        - JSON containing information describe in ReservationSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    current_date = datetime.today()
    start = current_date - timedelta(days=current_date.weekday())
    end = start + timedelta(days=6)

    query = Reservation.query.filter(
        Reservation.collect_date >= start, Reservation.collect_date <= end
    )
    if query is not None:
        data = ReservationSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}
    return abort(404, "Reservations not found")


@blueprint.route("/reservations_returns_of_day")
def reservations_returns_of_day():
    """API endpoint to list reservation.

    :return: A tuple:

        - JSON containing information describe in ReservationSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    current_date = datetime.today()
    start_week = current_date - timedelta(days=current_date.weekday())
    end_week = start_week + timedelta(days=6)

    query = Reservation.query.filter(
        Reservation.return_date <= end_week,
        Reservation.status == ReservationStatus.Ongoing,
    )
    if query is not None:
        data = ReservationSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}

    return abort(404, "Reservations not found")


@blueprint.route("/reservation/histo_reservations_for_an_equipment<int:equipment_id>")
def equipment_histo_reservations(equipment_id):
    """API endpoint to list the historique of reservations of an equipment.

    :return: A tuple:

        - JSON containing information describe in ReservationShema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Equipment.query.get(equipment_id).get_reservations()

    if query is not None:
        data = ReservationSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}
    return abort(404, "Reservations not found")


class ReservationLineSchema(marshmallow.Schema):
    """Schema to describe reservation line"""

    equipment_type_name = fields.Function(lambda obj: obj.equipment_type.name)

    reservation_line_url = fields.Function(
        lambda obj: url_for(
            "reservation.view_reservation_line", reservation_line_id=obj.id
        )
    )

    ratio_equipments = fields.Function(lambda obj: obj.get_ratio_equipments())

    total_price = fields.Function(lambda obj: obj.total_price_str())

    class Meta:
        """Fields to expose"""

        fields = (
            "quantity",
            "equipment_type_name",
            "reservation_line_url",
            "ratio_equipments",
            "total_price",
        )


@blueprint.route("/reservation/<int:reservation_id>")
def reservation_lines(reservation_id):
    """API endpoint to list reservation lines.

    :return: A tuple:

        - JSON containing information describe in ReservationLineSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Reservation.query.get(reservation_id).lines

    if query is not None:
        data = ReservationLineSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}
    return abort(404, "Reservation lines not found")


@blueprint.route("/reservation/new_rental/<int:reservation_id>")
def new_rental(reservation_id):
    """API endpoint to list reservation lines.

    :return: A tuple:

        - JSON containing information describe in ReservationLineSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Reservation.query.get(reservation_id).get_equipments()

    if query is not None:
        data = EquipmentSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}

    return abort(404, "Equipments not found")


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

    if query is not None:
        data = EquipmentSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}

    return abort(404, "Reservation line not found")


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

    if query is not None:
        data = EquipmentSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}

    return abort(404, "Equipments not found")


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

    if query is not None:
        data = EquipmentSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}

    return abort(404, "Equipments not found")


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
    if equipment is not None:
        equipment.status = EquipmentStatus.Available
        db.session.commit()

        return (
            "{'response': 'Status changed OK'}",
            200,
            {"content-type": "application/json"},
        )
    return abort(404, "Equipment not found")


@blueprint.route(
    "/remove_reservation_equipment/<int:equipment_id>/<int:reservation_id>",
    methods=["POST"],
)
@blueprint.route(
    "/remove_reservationLine_equipment/<int:equipment_id>/<int:line_id>",
    methods=["POST"],
)
def remove_reservation_equipment(equipment_id, reservation_id=None, line_id=None):
    """
    API endpoint to remove an equipment from a réservation.

    :return: A tuple:

        - JSON containing information if OK
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    equipment = Equipment.query.get(equipment_id)
    if equipment is not None:
        if reservation_id:
            reservation = Reservation.query.get(reservation_id)
            if not reservation.remove_equipment(equipment):
                return (
                    "{'response': 'Pas OK'}",
                    200,
                    {"content-type": "application/json"},
                )
        else:
            line = ReservationLine.query.get(line_id)
            line.remove_equipment(equipment)
        db.session.commit()

        return (
            "{'response': 'Status changed OK'}",
            200,
            {"content-type": "application/json"},
        )
    return abort(404, "Equipment not found")


@blueprint.route(
    "/remove_reservation_equipment_decreasing_quantity/<int:equipment_id>/<int:reservation_id>",
    methods=["POST"],
)
def remove_reservation_equipment_decreasing_quantity(equipment_id, reservation_id=None):
    """
    API endpoint to remove an equipment from a réservation.

    :return: A tuple:

        - JSON containing information if OK
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    equipment = Equipment.query.get(equipment_id)
    reservation = Reservation.query.get(reservation_id)
    if equipment is not None and reservation is not None:
        reservation.remove_equipment_decreasing_quantity(equipment)
        db.session.commit()

        return (
            "{'response': 'Status changed OK'}",
            200,
            {"content-type": "application/json"},
        )
    return abort(404, "Equipment or reservation not found")


@blueprint.route("/my_reservations/")
def my_reservations():
    """API endpoint to list reservation lines of current user.

    :return: A tuple:

        - JSON containing information describe in ReservationSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = User.query.get(current_user.id).get_reservations_planned_and_ongoing()
    if query is not None:
        data = ReservationSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}

    return abort(404, "No reservations found for this user")


@blueprint.route("/my_reservations_completed/")
def my_reservations_completed():
    """API endpoint to list reservation lines of current user.

    :return: A tuple:

        - JSON containing information describe in ReservationSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = User.query.get(current_user.id).get_reservations_completed()
    if query is not None:
        data = ReservationSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}
    return abort(404, "No reservation completed")


@blueprint.route("/my_reservation/<int:reservation_id>")
def my_reservation(reservation_id):
    """API endpoint to list reservation lines.

    :return: A tuple:

        - JSON containing information describe in ReservationLineSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    query = Reservation.query.get(reservation_id).lines

    if query is not None:
        data = ReservationLineSchema(many=True).dump(query)

        return json.dumps(data), 200, {"content-type": "application/json"}

    return abort(404, "Reservation not found")


class AutocompleteEquipmentSchema(marshmallow.Schema):
    """Schema to describe autocomplete equipment"""

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "reference",
        )


def find_equipments_by_reference(pattern):
    """Find equipment for autocomplete from a part of their full name.

    Comparison are case insensitive.

    :param string pattern: Part of the name that will be searched.
    :return: List of equipments corresponding to ``q``
    :rtype: list(:py:class:`collectives.models.equipment.Equipment`)
    """

    sql = "SELECT id, reference from equipments WHERE LOWER(reference) LIKE :pattern"

    sql_pattern = f"%{pattern.lower()}%"
    found_equipments = (
        db.session.query(Equipment)
        .from_statement(text(sql))
        .params(pattern=sql_pattern)
    )

    return found_equipments


@blueprint.route("/reservation/autocomplete/<int:line_id>")
@blueprint.route("/reservation/autocomplete")
def autocomplete_availables_equipments(line_id=None):
    """API endpoint to list equipment in a reservation line.

    :return: A tuple:

        - JSON containing information describe in EquipmentSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """

    pattern = request.args.get("q")

    equipments_of_autocomplete = []
    if pattern is None:
        return abort(404, "Autocomplete didn't succeed")
    equipments_of_autocomplete = find_equipments_by_reference(pattern)

    if line_id:
        equipment_type = ReservationLine.query.get(line_id).equipment_type
        equipments_of_type = equipment_type.get_all_equipments_availables()
        query = list(set(equipments_of_type).intersection(equipments_of_autocomplete))
    else:
        equipments_availables = Equipment.query.filter_by(
            status=EquipmentStatus.Available
        )
        query = list(
            set(equipments_availables).intersection(equipments_of_autocomplete)
        )

    if query is None:
        return abort(404, "Autocomplete didn't succeed")

    data = EquipmentSchema(many=True).dump(query)
    return json.dumps(data), 200, {"content-type": "application/json"}
