"""API for user list in administration page."""

import json

from flask import request, url_for
from flask_login import current_user
from marshmallow import fields
from sqlalchemy import and_, desc
from sqlalchemy.orm import joinedload, selectinload

from collectives.api.common import blueprint
from collectives.api.schemas import BadgeSchema, RoleSchema, UserSchema
from collectives.models import Badge, Role, RoleIds, User, db
from collectives.models.badge import BadgeIds
from collectives.utils.access import confidentiality_agreement, user_is, valid_user


class AdminUserSchema(UserSchema):
    """Schema for users in admin list"""

    roles_uri = fields.Function(
        lambda user: url_for("administration.add_user_role", user_id=user.id)
    )
    """ URI to role management page for this user

    :type: string
    """
    badges_uri = fields.Function(
        lambda user: url_for("administration.add_user_badge", user_id=user.id)
    )
    """ URI to badge management page for this user

    :type: string
    """
    delete_uri = fields.Function(
        lambda user: url_for("profile.delete_user", user_id=user.id)
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

    class Meta(UserSchema.Meta):
        """Fields to expose"""

        fields = (
            "id",
            "mail",
            "is_active",
            "enabled",
            "roles_uri",
            "badges_uri",
            "avatar_uri",
            "manage_uri",
            "profile_uri",
            "delete_uri",
            "first_name",
            "last_name",
            "roles",
            "badges",
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

        - JSON containing information describe in AdminUserSchema

        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """

    query = db.session.query(User)
    query = query.options(selectinload(User.roles), selectinload(User.badges))

    # Process all filters.
    # All filter are added as AND
    i = 0
    while f"filters[{i}][field]" in request.args:
        value = request.args.get(f"filters[{i}][value]")
        field = request.args.get(f"filters[{i}][field]")

        if value is None:
            i += 1
            continue

        if field == "roles":
            # if field is roles,

            filters = {i[0]: i[1:] for i in value.split("-")}
            if "r" in filters:
                filters["r"] = Role.role_id == RoleIds(int(filters["r"]))
            if "t" in filters:
                if filters["t"] == "none":
                    filters["t"] = None
                filters["t"] = Role.activity_id == filters["t"]

            filters = list(filters.values())
            query_filter = User.roles.any(and_(*filters))

        elif field == "badges":
            # if field is roles,

            filters = {i[0]: i[1:] for i in value.split("-")}
            if "b" in filters:
                filters["b"] = Badge.badge_id == BadgeIds(int(filters["b"]))
            if "t" in filters:
                if filters["t"] == "none":
                    filters["t"] = None
                filters["t"] = Badge.activity_id == filters["t"]

            filters = list(filters.values())
            query_filter = User.badges.any(and_(*filters))

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
    data = AdminUserSchema(many=True).dump(paginated_users.items)
    response = {"data": data, "last_page": paginated_users.pages}

    return response, 200, {"content-type": "application/json"}


class LeaderRoleSchema(RoleSchema):
    """Schema for a leader role

    Combines a :py:class:`UserSchema` and :py:class:`.event.ActivityTypeSchema`.
    """

    delete_uri = fields.Function(
        lambda role: (
            url_for("activity_supervision.remove_leader", role_id=role.id)
            if role.role_id in RoleIds.all_supervisor_manageable()
            else ""
        )
    )

    user = fields.Nested(UserSchema)

    class Meta(RoleSchema.Meta):
        """Fields to expose"""

        fields = (
            "user",
            "activity_type",
            "delete_uri",
            "name",
        )


class UserBadgeSchema(BadgeSchema):
    """Schema for a badge

    Combines a :py:class:`UserSchema` and :py:class:`.event.ActivityTypeSchema`.
    """

    delete_uri = fields.Function(
        lambda badge: url_for(
            request.args.get("delete", "activity_supervision.delete_volunteer"),
            badge_id=badge.id,
        )
    )
    renew_uri = fields.Function(
        lambda badge: url_for(
            request.args.get("renew", "activity_supervision.renew_volunteer"),
            badge_id=badge.id,
        )
    )

    user = fields.Nested(UserSchema)

    class Meta(BadgeSchema.Meta):
        """Fields to expose"""

        fields = (
            "user",
            "activity_type",
            "badge_id",
            "name",
            "expiration_date",
            "level",
            "delete_uri",
            "renew_uri",
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
    query = query.options(
        joinedload(Role.user).selectinload(User.roles),
        joinedload(Role.user).selectinload(User.badges),
    )
    query = query.filter(Role.role_id.in_(RoleIds.all_relates_to_activity()))
    query = query.filter(Role.activity_id.in_(a.id for a in supervised_activities))
    query = query.join(Role.user)
    query = query.order_by(User.last_name, User.first_name, User.id)

    response = LeaderRoleSchema(many=True).dump(query.all())

    return json.dumps(response), 200, {"content-type": "application/json"}


@blueprint.route("/badges/")
@valid_user(True)
@user_is(["is_supervisor", "is_hotline"], api=True)
@confidentiality_agreement(True)
def badges():
    """API endpoint to list current badges

    Only available to administrators and activity supervisors

    :return: A tuple:

        - JSON containing information describe in UserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """
    if current_user.is_hotline():
        supervised_activities = None
    else:
        supervised_activities = current_user.get_supervised_activities()

    badge_ids = request.args.getlist("badge_ids", type=int)
    badge_ids = [BadgeIds(badge_id) for badge_id in badge_ids]

    query = db.session.query(Badge)
    query = query.options(
        joinedload(Badge.user).selectinload(User.roles),
        joinedload(Badge.user).selectinload(User.badges),
    )
    if badge_ids:
        query = query.filter(Badge.badge_id.in_(badge_ids))
    if supervised_activities:
        query = query.filter(
            Badge.activity_id.in_(a.id for a in supervised_activities),
        )
    query = query.join(Badge.user)
    query = query.order_by(User.last_name, User.first_name, User.id)

    badges_list = query.all()

    for badge in badges_list:
        badge.delete_uri = url_for(
            request.args.get("delete", "activity_supervision.delete_volunteer"),
            badge_id=badge.id,
        )
        badge.renew_uri = url_for(
            request.args.get("renew", "activity_supervision.renew_volunteer"),
            badge_id=badge.id,
        )

    response = UserBadgeSchema(many=True).dump(badges_list)

    return json.dumps(response), 200, {"content-type": "application/json"}
