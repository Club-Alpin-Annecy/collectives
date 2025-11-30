"""API for user list in administration page."""

import json

from flask import request, url_for, abort
from flask_login import current_user
from marshmallow import fields
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import aliased, selectinload

from collectives.api.common import blueprint
from collectives.api.schemas import (
    BadgeSchema,
    RoleSchema,
    UserIdentitySchema,
    UserSchema,
)
from collectives.models import Badge, Role, RoleIds, User, db, ActivityType
from collectives.models.badge import BadgeIds, BadgeCustomLevel
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

    user = fields.Nested(UserIdentitySchema)

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

    user = fields.Nested(UserIdentitySchema)

    grantor = fields.Nested(UserIdentitySchema)

    class Meta(BadgeSchema.Meta):
        """Fields to expose"""

        fields = (
            "user",
            "grantor",
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
    query = query.filter(Role.role_id.in_(RoleIds.all_relates_to_activity()))
    query = query.filter(Role.activity_id.in_(a.id for a in supervised_activities))
    query = query.join(Role.user).join(Role.activity_type)

    # Process filters coming from Tabulator (filters[0]...)
    i = 0
    while f"filters[{i}][field]" in request.args:
        value = request.args.get(f"filters[{i}][value]")
        field = request.args.get(f"filters[{i}][field]")
        i += 1

        if value is None:
            continue

        # support nested fields like 'user.full_name' or 'activity_type.name'
        if "." in field:
            prefix, sub = field.split(".", 1)
            if prefix == "user":
                if sub != "full_name":
                    continue
                query_filter = User.full_name().ilike(f"%{value}%")
            elif prefix == "activity_type":
                try:
                    activity_id = int(value)
                    query_filter = Role.activity_id == activity_id
                except ValueError:
                    continue
            else:
                continue
        elif field == "name":
                try:
                    role_id = int(value)
                    query_filter = Role.role_id == RoleIds(role_id)
                except ValueError:
                    continue
        else:
            continue


        query = query.filter(query_filter)

    # Sorting
    if "sorters[0][field]" in request.args:
        sort_field = request.args.get("sorters[0][field]")
        sort_dir = request.args.get("sorters[0][dir]")
        if sort_field == "user.full_name":
            sort_field = User.full_name()
        elif sort_field == "activity_type.name":
            sort_field = ActivityType.name
        elif sort_field == "name":
            sort_field = Role.role_id
        order = desc(sort_field) if sort_dir == "desc" else sort_field
        query = query.order_by(order)
    else:
        query = query.order_by(User.last_name, User.first_name, User.id)

    # Pagination (Tabulator expects 'page' and 'size')
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 50))
    paginated = query.paginate(page=page, per_page=size, error_out=False)

    response = LeaderRoleSchema(many=True).dump(paginated.items)
    return (
        {"data": response, "last_page": paginated.pages},
        200,
        {"content-type": "application/json"},
    )


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
    if badge_ids:
        query = query.filter(Badge.badge_id.in_(badge_ids))
    if supervised_activities:
        query = query.filter(Badge.activity_id.in_(a.id for a in supervised_activities))

    Recipient = aliased(User)
    query = query.join(Recipient, Badge.user)
    query = query.join(Badge.grantor, isouter=True)
    query = query.join(Badge.activity_type, isouter=True)
    query = query.join(
        BadgeCustomLevel,
        and_(
            BadgeCustomLevel.badge_id == Badge.badge_id,
            BadgeCustomLevel.level == Badge.level,
            BadgeCustomLevel.activity_id.isnot_distinct_from(Badge.activity_id),
        ),
        isouter=True,
    )

    # Process Tabulator filters
    i = 0
    while f"filters[{i}][field]" in request.args:
        value = request.args.get(f"filters[{i}][value]")
        field = request.args.get(f"filters[{i}][field]")
        i += 1

        if value is None:
            continue

        if "." in field:
            prefix, sub = field.split(".", 1)
            if prefix == "user":
                if sub != "full_name":
                    continue
                query_filter = Recipient.full_name().ilike(f"%{value}%")
            elif prefix == "grantor":
                if sub != "full_name":
                    continue
                query_filter = User.full_name().ilike(f"%{value}%")
            elif prefix == "activity_type":
                try:
                    activity_id = int(value)
                    query_filter = Badge.activity_id == activity_id
                except ValueError:
                    continue
            else:
                continue
        elif field == "name":
            try:
                badge_id = int(value)
                query_filter = Badge.badge_id == BadgeIds(badge_id)
            except ValueError:
                continue
        elif field == "level":
            value = value.lower()
            default_levels = {
                badge_id: [
                    level
                    for level, desc in badge_id.levels(only_defaults=True).items()
                    if value in desc.name.lower()
                ]
                for badge_id in badge_ids or BadgeIds
            }
            default_level_clauses = [
                and_(Badge.badge_id == badge_id, Badge.level.in_(levels))
                for badge_id, levels in default_levels.items()
                if levels
            ]
            query_filter = or_(
                *default_level_clauses,
                BadgeCustomLevel.name.ilike(f"%{value}%"),
            )
        elif field in ("expiration_date",):
            query_filter = getattr(Badge, field).ilike(f"%{value}%")

        query = query.filter(query_filter)

    # Sorting
    if "sorters[0][field]" in request.args:
        sort_field = request.args.get("sorters[0][field]")
        sort_dir = request.args.get("sorters[0][dir]")
        if sort_field == "user.full_name":
            sort_field = Recipient.full_name()
        elif sort_field == "grantor.full_name":
            sort_field = User.full_name()
        elif sort_field == "activity_type.name":
            sort_field = ActivityType.name
        elif sort_field == "name":
            sort_field = Badge.badge_id
        order = desc(sort_field) if sort_dir == "desc" else sort_field
        query = query.order_by(order)
    else:
        query = query.order_by(Recipient.last_name, Recipient.first_name, Recipient.id)

    # Pagination
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 50))
    paginated = query.paginate(page=page, per_page=size, error_out=False)

    response = UserBadgeSchema(many=True).dump(paginated.items)
    return (
        {"data": response, "last_page": paginated.pages},
        200,
        {"content-type": "application/json"},
    )
