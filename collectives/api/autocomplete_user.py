"""API for autocomplete users name.

Especially used for user registration by leader in events.

"""

import json

from flask import request, abort
from flask_login import current_user
from sqlalchemy.orm import Query
from sqlalchemy import func, and_

from collectives.api.common import blueprint
from collectives.api.schemas import UserSchema
from collectives.models import db, User, Role, RoleIds, EventType
from collectives.utils.access import confidentiality_agreement, valid_user


class AutocompleteUserSchema(UserSchema):
    """Schema under which autocomplete suggestions are returned"""

    class Meta(UserSchema.Meta):
        """Fields to expose"""

        fields = (
            "id",
            "full_name",
            "is_active",
        )


def _make_autocomplete_query(pattern: str) -> Query:
    """Builds the autocomplete query for the provided pattern"""

    query = db.session.query(User)
    query = query.filter(func.lower(User.full_name()).like(f"%{pattern}%"))
    query = query.order_by(User.is_active.desc(), User.full_name(), User.id)

    return query


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
        limit = request.args.get("l", default=8, type=int)
        found_users = _make_autocomplete_query(pattern).limit(limit)

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
        limit = request.args.get("l", default=8, type=int)
        found_users = _make_autocomplete_query(pattern).limit(limit)

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
        limit = request.args.get("l", default=8, type=int)

        query = _make_autocomplete_query(pattern)
        query = query.filter(User.led_events)
        found_users = query.limit(limit)

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
        limit = request.args.get("l", default=8, type=int)

        query = _make_autocomplete_query(pattern)
        event_type = db.session.get(
            EventType, request.args.get("etype", type=int, default=0)
        )
        activity_ids = request.args.getlist("aid", type=int)
        existing_ids = request.args.getlist("eid", type=int)

        if event_type and event_type.requires_activity:
            ok_roles = RoleIds.all_activity_leader_roles()
        else:
            ok_roles = RoleIds.all_event_creator_roles()
        role_condition = Role.role_id.in_(ok_roles)
        if len(activity_ids) > 0:
            role_condition = and_(role_condition, Role.activity_id.in_(activity_ids))
        query = query.filter(User.roles.any(role_condition))
        query = query.filter(~User.id.in_(existing_ids))

        found_users = query.limit(limit)

    content = json.dumps(AutocompleteUserSchema(many=True).dump(found_users))
    return content, 200, {"content-type": "application/json"}
