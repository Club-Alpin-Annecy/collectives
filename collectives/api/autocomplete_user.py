""" API for autocomplete users name.

Especially used for user registration by leader in events.

"""

import json

from flask import request, abort
from flask_login import current_user
from sqlalchemy.sql import text
from sqlalchemy import func
from marshmallow import fields

from ..models import db, User

from ..utils.access import confidentiality_agreement, valid_user
from .common import blueprint, marshmallow


class AutocompleteUserSchema(marshmallow.Schema):
    """  Schema under which autocomplete suggestions are returned """

    full_name = fields.Function(lambda user: user.full_name())
    """ User full name as :py:meth:`collectives.models.user.User.full_name`

    :type: string"""

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "full_name",
        )


def find_users_by_fuzzy_name(q, limit=8):
    """Find user for autocomplete from a part of their full name.

    Comparison are case insensitive.

    :param string q: Part of the name that will be searched.
    :param int limit: Maximum number of response.
    :return: List of users corresponding to ``q``
    :rtype: list(:py:class:`collectives.models.user.User`)
    """
    if db.session.bind.dialect.name == "sqlite":
        # SQLlite does not follow SQL standard
        concat_clause = "(first_name || ' ' || last_name)"
    else:
        concat_clause = "CONCAT(first_name, ' ', last_name)"

    sql = (
        "SELECT id, first_name, last_name from users "
        "WHERE LOWER({}) LIKE :pattern LIMIT :limit"
    ).format(concat_clause)

    pattern = "%{}%".format(q.lower())
    found_users = (
        db.session.query(User)
        .from_statement(text(sql))
        .params(pattern=pattern, limit=limit)
    )

    return found_users


@blueprint.route("/users/autocomplete/")
@valid_user(True)
@confidentiality_agreement(True)
def autocomplete_users():
    """API endpoint to list users for autocomplete.

    At least 2 characters are required to make a name search.

    :return: A tuple:

        - JSON containing information describe in AutocompleteUserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """
    if not current_user.can_create_events():
        abort(403)

    q = request.args.get("q")
    if q is None or (len(q) < 2):
        found_users = []
    else:
        found_users = find_users_by_fuzzy_name(q)

    content = json.dumps(AutocompleteUserSchema(many=True).dump(found_users))
    return content, 200, {"content-type": "application/json"}


@blueprint.route("/leaders/autocomplete/")
def autocomplete_leaders():
    """API endpoint to list leaders for autocomplete.

    At least 2 characters are required to make a name search.

    :return: A tuple:

        - JSON containing information describe in AutocompleteUserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """

    q = request.args.get("q").lower()
    if q is None or (len(q) < 2):
        found_users = []
    else:
        query = db.session.query(User)
        condition = func.lower(User.first_name + " " + User.last_name).like(f"%{q}%")
        query = query.filter(condition)
        query = query.filter(User.led_events)
        found_users = query.order_by(User.id).all()
        found_users = found_users[0:8]

    content = json.dumps(AutocompleteUserSchema(many=True).dump(found_users))
    return content, 200, {"content-type": "application/json"}
