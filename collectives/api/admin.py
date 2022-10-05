""" API for user list in administration page.

"""
import json

from flask import url_for, request
from flask_login import current_user
from marshmallow import fields
from sqlalchemy import desc, and_

from collectives.models import db, User, RoleIds, Role
from collectives.utils.access import valid_user, user_is, confidentiality_agreement

from collectives.api.common import blueprint, marshmallow, avatar_url
from collectives.api.event import ActivityTypeSchema


class RoleSchema(marshmallow.Schema):
    """Schema for the role of a user.

    Mainly used in :py:attr:`UserSchema.roles`
    """

    class Meta:
        """Fields to expose"""

        fields = (
            "name",
            "role_id",
            "activity_type.name",
            "activity_type.short",
        )


class UserSchema(marshmallow.Schema):
    """Schema of a user to be used to extract API information.

    This class is a ``marshmallow`` schema which automatically gets its
    structure from the ``User`` class. Plus, we add some useful information
    or link. This schema is only used for administration listing.
    """

    isadmin = fields.Function(lambda user: user.is_admin())
    """ Wraps :py:meth:`collectives.models.user.User.is_admin`

    :type: boolean"""
    roles_uri = fields.Function(
        lambda user: url_for("administration.add_user_role", user_id=user.id)
    )
    """ URI to role management page for this user

    :type: string
    """
    delete_uri = fields.Function(
        lambda user: url_for("administration.delete_user", user_id=user.id)
    )
    """ URI to delete this user (WIP)

    :type: string
    """
    manage_uri = fields.Function(
        lambda user: url_for("administration.manage_user", user_id=user.id)
    )
    """ URI to modify this user

    :type: string
    """
    profile_uri = fields.Function(
        lambda user: url_for("profile.show_user", user_id=user.id)
    )
    """ URI to see user profile

    :type: string
    """
    leader_profile_uri = fields.Function(
        lambda user: url_for("profile.show_leader", leader_id=user.id)
        if user.can_create_events()
        else None
    )
    """ URI to see user profile

    :type: string
    """
    avatar_uri = fields.Function(avatar_url)
    """ URI to a resized version (30px) of user avatar

    :type: string
    """
    roles = fields.Function(lambda user: RoleSchema(many=True).dump(user.roles))
    """ List of roles of the User.

    Roles are encoded as JSON.

    :type: list(dict())"""
    full_name = fields.Function(lambda user: user.full_name())
    """ User full name

    :type: string"""

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "mail",
            "isadmin",
            "enabled",
            "roles_uri",
            "avatar_uri",
            "manage_uri",
            "profile_uri",
            "delete_uri",
            "first_name",
            "last_name",
            "roles",
            "isadmin",
            "leader_profile_uri",
            "full_name",
        )


@blueprint.route("/users/")
@valid_user(True)
@user_is("is_hotline", True)
@confidentiality_agreement(True)
def users():
    """API endpoint to list users

    Only available to administrators

    :return: A tuple:

        - JSON containing information describe in UserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """

    query = db.session.query(User)

    # Process all filters.
    # All filter are added as AND
    i = 0
    while f"filters[{i}][field]" in request.args:
        value = request.args.get(f"filters[{i}][value]")
        field = request.args.get(f"filters[{i}][field]")

        if field == "roles":
            # if field is roles,

            filters = {i[0]: i[1:] for i in value.split("-")}
            if "r" in filters:
                filters["r"] = Role.role_id == RoleIds.get(filters["r"])
            if "t" in filters:
                if filters["t"] == "none":
                    filters["t"] = None
                filters["t"] = Role.activity_id == filters["t"]

            filters = list(filters.values())
            query_filter = User.roles.any(and_(*filters))

        else:
            query_filter = getattr(User, field).ilike(f"%{value}%")

        query = query.filter(query_filter)
        # Get next filter
        i += 1

    # Process first sorter only
    if "sorters[0][field]" in request.args:
        sort_field = request.args.get("sorters[0][field]")
        sort_dir = request.args.get("sorters[0][dir]")
        order = desc(sort_field) if sort_dir == "desc" else sort_field
        query = query.order_by(order)

    # Pagination block
    page = int(request.args.get("page"))
    size = int(request.args.get("size"))
    paginated_users = query.paginate(page=page, per_page=size, error_out=False)
    data = UserSchema(many=True).dump(paginated_users.items)
    response = {"data": data, "last_page": paginated_users.pages}

    return response, 200, {"content-type": "application/json"}


class LeaderRoleSchema(marshmallow.Schema):
    """Schema for a leader role

    Combines a :py:class:`UserSchema` and :py:class:`.event.ActivityTypeSchema`.
    """

    delete_uri = fields.Function(
        lambda role: url_for("activity_supervision.remove_leader", role_id=role.id)
        if role.role_id in RoleIds.all_supervisor_manageable()
        else ""
    )
    """ URI to delete this user (WIP)

    :type: string
    """
    user = fields.Function(lambda role: UserSchema().dump(role.user))
    """ URI to a resized version (30px) of user avatar

    :type: string
    """

    activity_type = fields.Function(
        lambda role: ActivityTypeSchema().dump(role.activity_type)
    )
    """ List of roles of the User.

    Roles are encoded as JSON.

    :type: list(dict())"""

    type = fields.Function(lambda role: role.role_id.display_name())
    """ Role type

    :type: string"""

    class Meta:
        """Fields to expose"""

        fields = (
            "user",
            "activity_type",
            "delete_uri",
            "type",
        )


@blueprint.route("/leaders/")
@valid_user(True)
@user_is("is_supervisor", True)
@confidentiality_agreement(True)
def leaders():
    """API endpoint to list current leaders

    Only available to administrators and activity supervisors

    :return: A tuple:

        - JSON containing information describe in UserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """

    supervised_activities = current_user.get_supervised_activities()

    query = db.session.query(Role)
    query = query.filter(
        Role.role_id.in_(
            [RoleIds.Trainee, RoleIds.EventLeader, RoleIds.ActivitySupervisor]
        )
    )
    query = query.filter(Role.activity_id.in_(a.id for a in supervised_activities))
    query = query.join(Role.user)
    query = query.order_by(User.last_name, User.first_name, User.id)

    response = LeaderRoleSchema(many=True).dump(query.all())

    return json.dumps(response), 200, {"content-type": "application/json"}
