"""API used to get events linked to a user for profiles.

Event schema is the one from :py:class:`collectives.api.event.EventSchema`
"""

import json

from flask_login import current_user
from marshmallow import fields
from sqlalchemy.orm import selectinload

from collectives.api.common import blueprint, marshmallow
from collectives.api.event import filter_hidden_events
from collectives.api.schemas import EventSchema
from collectives.models import Event, Registration, User, db
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
        return "[]", 403, {"content-type": "application/json"}

    query = db.session.query(Event)
    query = query.options(
        selectinload(Event.tag_refs), selectinload(Event.registrations)
    )
    query = filter_hidden_events(query)

    query = query.filter(Registration.user_id == user_id)
    query = query.filter(Event.id == Registration.event_id)
    query = query.order_by(Event.start, Event.id)

    events = query.all()

    user = db.session.get(User, user_id)
    for event in events:
        event.registration = event.existing_registrations(user)[0]

    response = RegistrationEventSchema(many=True).dump(events)
    return json.dumps(response), 200, {"content-type": "application/json"}


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
        return "[]", 403, {"content-type": "application/json"}

    query = db.session.query(Event)
    query = query.options(
        selectinload(Event.tag_refs), selectinload(Event.registrations)
    )
    query = filter_hidden_events(query)

    query = query.filter(Event.leaders.contains(leader))
    query = query.order_by(Event.start, Event.id)

    result = query.all()
    response = EventSchema(many=True).dump(result)

    return json.dumps(response), 200, {"content-type": "application/json"}
