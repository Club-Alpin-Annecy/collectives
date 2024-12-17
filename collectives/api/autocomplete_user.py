""" API for autocomplete users name.

Especially used for user registration by leader in events.

"""

import json

from flask import request, abort
from flask_login import current_user
from sqlalchemy.sql import text
from sqlalchemy import func, and_
from marshmallow import fields

from collectives.api.common import blueprint, marshmallow
from collectives.models import db, User, Role, RoleIds, EventType
from collectives.utils.access import confidentiality_agreement, valid_user


class AutocompleteUserSchema(marshmallow.Schema):
    """Schema under which autocomplete suggestions are returned"""

    full_name = fields.Function(lambda user: user.full_name())
    """ User full name as :py:meth:`collectives.models.user.User.full_name`

    :type: string"""

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "full_name",
            "license_expiry_date",
        )


def find_users_by_fuzzy_name(pattern, limit=8):
    """Find user for autocomplete from a part of their full name.

    Comparison are case insensitive.

    :param string pattern: Part of the name that will be searched.
    :param int limit: Maximum number of response.
    :return: List of users corresponding to ``pattern``
    :rtype: list(:py:class:`collectives.models.user.User`)
    """
    if "sqlite" in db.engine.name:
        # SQLlite does not follow SQL standard
        concat_clause = "(first_name || ' ' || last_name)"
    else:
        concat_clause = "CONCAT(first_name, ' ', last_name)"

    sql = (
        f"SELECT id, first_name, last_name from users WHERE "
        f"LOWER({concat_clause}) LIKE :pattern LIMIT :limit"
    )

    sql_pattern = f"%{pattern.lower()}%"
    found_users = (
        db.session.query(User)
        .from_statement(text(sql))
        .params(pattern=sql_pattern, limit=limit)
    )

    return found_users


@blueprint.route("/users/autocomplete/create_rental")
@valid_user(True)
@confidentiality_agreement(True)
def autocomplete_users_create_rental():
    """API endpoint to list users for autocomplete.

    At least 2 characters are required to make a name search.

    :param string q: Search string.
    :param int l: Maximum number of returned items.
    :return: A tuple:

        - JSON containing information describe in AutocompleteUserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """
    # if not current_user.can_create_events():
    #     abort(403)

    pattern = request.args.get("q")
    if pattern is None or (len(pattern) < 2):
        found_users = []
    else:
        limit = request.args.get("l", type=int) or 8
        found_users = find_users_by_fuzzy_name(pattern, limit)

    content = json.dumps(AutocompleteUserSchema(many=True).dump(found_users))
    return content, 200, {"content-type": "application/json"}


@blueprint.route("/users/autocomplete/")
@valid_user(True)
@confidentiality_agreement(True)
def autocomplete_users():
    """API endpoint to list users for autocomplete.

    At least 2 characters are required to make a name search.

    :param string q: Search string.
    :param int l: Maximum number of returned items.
    :return: A tuple:

        - JSON containing information describe in AutocompleteUserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """
    if not current_user.can_create_events():
        abort(403)

    pattern = request.args.get("q")
    if pattern is None or (len(pattern) < 2):
        found_users = []
    else:
        limit = request.args.get("l", type=int) or 8
        found_users = find_users_by_fuzzy_name(pattern, limit)

    content = json.dumps(AutocompleteUserSchema(many=True).dump(found_users))
    return content, 200, {"content-type": "application/json"}


@blueprint.route("/leaders/autocomplete/")
def autocomplete_leaders():
    """API endpoint to list leaders for autocomplete.

    At least 2 characters are required to make a name search.

    :param string q: Search string.
    :param int l: Maximum number of returned items.
    :return: A tuple:

        - JSON containing information describe in AutocompleteUserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """

    pattern = request.args.get("q", "").lower()
    if len(pattern) < 2:
        found_users = []
    else:
        limit = request.args.get("l", type=int) or 8

        query = db.session.query(User)
        condition = func.lower(User.first_name + " " + User.last_name).like(
            f"%{pattern}%"
        )
        query = query.filter(condition)
        query = query.filter(User.led_events)
        found_users = query.order_by(User.id).all()
        found_users = found_users[0:limit]

    content = json.dumps(AutocompleteUserSchema(many=True).dump(found_users))
    return content, 200, {"content-type": "application/json"}


@blueprint.route("/available_leaders/autocomplete/")
def autocomplete_available_leaders():
    """API endpoint to list available leaders for autocomplete. In contrast with the
    previous function this also includes leaders that have never led any event.

    At least 2 characters are required to make a name search.

    :param string q: Search string.
    :param int l: Maximum number of returned items.
    :param list[int] aid: List of activity ids to include. Empty means include leaders
                          of any activity
    :param list[int] eid: List of leader ids to exclude
    :param int etype: Id of event type
    :return: A tuple:

        - JSON containing information describe in AutocompleteUserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """

    pattern = request.args.get("q")
    if pattern is None or (len(pattern) < 2):
        found_users = []
    else:
        limit = request.args.get("l", type=int) or 8
        event_type = db.session.get(
            EventType, request.args.get("etype", type=int, default=0)
        )
        activity_ids = request.args.getlist("aid", type=int)
        existing_ids = request.args.getlist("eid", type=int)

        query = db.session.query(User)

        if event_type and event_type.requires_activity:
            ok_roles = RoleIds.all_activity_leader_roles()
        else:
            ok_roles = RoleIds.all_event_creator_roles()
        role_condition = Role.role_id.in_(ok_roles)
        if len(activity_ids) > 0:
            role_condition = and_(role_condition, Role.activity_id.in_(activity_ids))
        query = query.filter(User.roles.any(role_condition))
        query = query.filter(~User.id.in_(existing_ids))
        condition = func.lower(User.first_name + " " + User.last_name).ilike(
            f"%{pattern}%"
        )
        query = query.filter(condition)

        query = query.order_by(User.first_name, User.last_name, User.id)
        found_users = query.limit(limit)

    content = json.dumps(AutocompleteUserSchema(many=True).dump(found_users))
    return content, 200, {"content-type": "application/json"}
