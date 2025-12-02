"""API used to get events linked to a user for profiles.

Event schema is the one from :py:class:`collectives.api.event.EventSchema`
"""

import json

import flask
from flask_login import current_user
from marshmallow import fields
from sqlalchemy import desc
from sqlalchemy.orm import selectinload

from collectives.api.common import blueprint, marshmallow
from collectives.api.event import filter_hidden_events
from collectives.api.schemas import EventSchema
from collectives.models import (
    ActivityType,
    Event,
    EventStatus,
    EventTag,
    EventType,
    Registration,
    RegistrationStatus,
    User,
    db,
)
from collectives.utils.access import valid_user


class RegistrationSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema to describe a registration"""

    status = fields.Function(lambda reg: reg.status.value)
    """Status of the registration, as an int for backward compatibility"""

    level = fields.Function(lambda reg: reg.level.value)
    """Level of the registration, as an int for backward compatibility"""

    class Meta:
        """Fields to expose"""

        model = Registration
        fields = ("id", "status", "level", "is_self")


class RegistrationEventSchema(EventSchema):
    """Schema to describe a en event with a specific registration"""

    registration = fields.Function(
        lambda event: RegistrationSchema().dump(event.registration)
    )

    class Meta:
        """Fields to expose"""

        fields = (*EventSchema.Meta.fields, "registration")


def _apply_ajax_filters_and_sorters(query):
    # Process filters coming from Tabulator (filters[0]...)
    i = 0
    while f"filters[{i}][field]" in flask.request.args:
        value = flask.request.args.get(f"filters[{i}][value]")
        field = flask.request.args.get(f"filters[{i}][field]")
        type_ = flask.request.args.get(f"filters[{i}][type]", "=")
        i += 1
        print(value, field, type_)

        if value is None:
            continue

        if field == "registration.status":
            if type_ == "in":
                try:
                    status_values = [
                        RegistrationStatus(int(v)) for v in value.split(",")
                    ]
                except ValueError:
                    continue
                query = query.filter(Registration.status.in_(status_values))
                continue

            try:
                registration_status = RegistrationStatus(int(value))
            except ValueError:
                continue
            if type_ in ("=", "like"):
                query = query.filter(Registration.status == registration_status)
            elif type_ == "!=":
                query = query.filter(Registration.status != registration_status)
        elif field == "event_type":
            query = query.filter(Event.event_type_id == int(value))
        elif field == "tags":
            query = query.filter(Event.tag_refs.any(EventTag.type == int(value)))
        elif field == "activity_types":
            query = query.filter(
                Event.activity_types.any(ActivityType.id == int(value))
            )
        elif field == "status":
            try:
                status = EventStatus(int(value))
            except ValueError:
                continue
            query = query.filter(Event.status == status)
        elif field == "leaders":
            query = query.filter(
                Event.leaders.any(User.full_name().ilike(f"%{value}%"))
            )
        elif field == "title":
            query = query.filter(Event.title.ilike(f"%{value}%"))
        elif field == "end":
            if type_ == ">":
                query = query.filter(Event.end > value)
            elif type_ == "<":
                query = query.filter(Event.end < value)
        elif field == "start":
            if type_ == ">":
                query = query.filter(Event.start > value)
            elif type_ == "<":
                query = query.filter(Event.start < value)

    # Process first sorter only
    if "sorters[0][field]" in flask.request.args:
        sort_field = flask.request.args.get("sorters[0][field]")
        sort_dir = flask.request.args.get("sorters[0][dir]")

        sort_attr = getattr(Event, sort_field, None)
        if sort_attr is not None:
            order = sort_attr.desc() if sort_dir == "desc" else sort_attr
            query = query.order_by(order)
        else:
            query = query.order_by(Event.start, Event.id)
    else:
        query = query.order_by(Event.start, Event.id)

    return query


@blueprint.route("/user/<user_id>/events")
@valid_user(True)
def user_events(user_id):
    """Get all event of a user.

    Users without roles can only see their own events.

    :param int user_id: ID of the user.
    :return: A tuple:

        - JSON containing information describe in EventSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """
    if int(user_id) != current_user.id and not current_user.can_read_other_users():
        return (
            json.dumps({"data": [], "last_page": 1, "total": 0}),
            403,
            {"content-type": "application/json"},
        )

    query = db.session.query(Event)
    query = query.join(Registration, Event.id == Registration.event_id)
    query = query.options(
        selectinload(Event.tag_refs), selectinload(Event.registrations)
    )
    query = filter_hidden_events(query)
    query = query.filter(Registration.user_id == user_id)

    query = _apply_ajax_filters_and_sorters(query)

    # Tabulator remote pagination/filtering params
    page = int(flask.request.args.get("page", 1))
    size = int(flask.request.args.get("size", 10))
    paginated = query.paginate(page=page, per_page=size, error_out=False)

    events = paginated.items

    user = db.session.get(User, user_id)
    for event in events:
        event.registration = event.existing_registrations(user)[0]

    response = RegistrationEventSchema(many=True).dump(events)
    last_page = paginated.pages
    return (
        json.dumps({"data": response, "last_page": last_page}),
        200,
        {"content-type": "application/json"},
    )


# Get all lead events of a leader
@blueprint.route("/leader/<leader_id>/events")
@valid_user(True)
def leader_events(leader_id):
    """Get all event of a leader.

    :param int user_id: ID of the user.
    :return: A tuple:

        - JSON containing information describe in EventSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """
    leader = User.query.filter_by(id=leader_id).first()

    if leader is None or not leader.can_create_events():
        return (
            json.dumps({"data": [], "last_page": 1, "total": 0}),
            403,
            {"content-type": "application/json"},
        )

    # Tabulator remote pagination/filtering params
    page = int(flask.request.args.get("page", 1))
    size = int(flask.request.args.get("size", 10))

    query = db.session.query(Event)
    query = query.options(
        selectinload(Event.tag_refs), selectinload(Event.registrations)
    )
    query = filter_hidden_events(query)
    query = query.filter(Event.leaders.contains(leader))

    query = _apply_ajax_filters_and_sorters(query)

    # Tabulator remote pagination/filtering params
    page = int(flask.request.args.get("page", 1))
    size = int(flask.request.args.get("size", 10))
    paginated = query.paginate(page=page, per_page=size, error_out=False)

    events = paginated.items

    response = EventSchema(many=True).dump(events)
    return (
        json.dumps({"data": response, "last_page": paginated.pages}),
        200,
        {"content-type": "application/json"},
    )
