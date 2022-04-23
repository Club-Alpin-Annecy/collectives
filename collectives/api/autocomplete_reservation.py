""" API for autocomplete equipment type names and images.

Especially used for reservations by leaders.

"""
import json
from flask import request, abort

from collectives.models.equipment import EquipmentType
from .common import blueprint, marshmallow


class AutocompleteEquipmentTypeSchema(marshmallow.Schema):
    """Schema to describe autocomplete equipment type"""

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "name",
        )


@blueprint.route("/reservation/types/autocomplete/")
def find_equipment_types():
    """Find equipment types for autocomplete from a part of their full name.
    Comparison are case insensitive.
    :param string q: Part of the name that will be searched.
    :param list[int] eid: List of type ids to exclude
    :return: List of equipment types corresponding to ``q``
    :rtype: list(:py:class:`collectives.models.equipment.EquipmentType`)
    """

    found_types = []

    search_term = request.args.get("q")
    if not search_term:
        abort(400)

    excluded_ids = request.args.getlist("eid", type=int)
    query = EquipmentType.query

    # Search term in name
    search_clause = EquipmentType.name.ilike(f"%{search_term}%")
    query = query.filter(search_clause)

    # Remove excluded ids
    found_types = query.filter(~EquipmentType.id.in_(excluded_ids))

    content = json.dumps(AutocompleteEquipmentTypeSchema(many=True).dump(found_types))
    return content, 200, {"content-type": "application/json"}
