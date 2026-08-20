"""API used to list events and their retex status for the Ptirex feature."""

import json

import flask
from flask_login import current_user
from marshmallow import fields

from collectives.api.common import blueprint
from collectives.api.schemas import EventSchema
from collectives.models import ActivityType, Event, EventType, db
from collectives.utils.access import user_is, valid_user
from collectives.utils.time import current_time


class RetexEventSchema(EventSchema):
    """Schema to describe an event along with its retex status"""

    has_retex = fields.Function(lambda event: event.retex is not None)
    """Whether this event already has a retex"""

    retex_status = fields.Function(
        lambda event: event.retex.status.value if event.retex else None
    )
    """Status of the retex, if any, as an int"""

    class Meta:
        """Fields to expose"""

        model = Event
        fields = (*EventSchema.Meta.fields, "has_retex", "retex_status")


@blueprint.route("/retex/mine")
@valid_user(True)
def mine():
    """API endpoint to list past collective events led by the current user.

    Paginated using ``page`` and ``size`` GET parameters.

    :return: A tuple:

        - JSON containing information described in RetexEventSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    query = db.session.query(Event)
    query = query.join(EventType)
    query = query.filter(Event.leaders.contains(current_user))
    query = query.filter(EventType.short == "collective")
    query = query.filter(Event.end < current_time())
    query = query.order_by(Event.end.desc())

    page = int(flask.request.args.get("page", 1))
    size = int(flask.request.args.get("size", 20))
    paginated = query.paginate(page=page, per_page=size, error_out=False)

    response = RetexEventSchema(many=True).dump(paginated.items)
    return (
        json.dumps({"data": response, "last_page": paginated.pages}),
        200,
        {"content-type": "application/json"},
    )


@blueprint.route("/retex/supervised")
@valid_user(True)
@user_is("is_supervisor", True)
def supervised():
    """API endpoint to list past collective events for the activities supervised
    by the current user.

    Paginated using ``page`` and ``size`` GET parameters.

    :return: A tuple:

        - JSON containing information described in RetexEventSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    activity_ids = {a.id for a in current_user.get_supervised_activities()}

    query = db.session.query(Event)
    query = query.join(EventType)
    query = query.filter(EventType.short == "collective")
    query = query.filter(Event.activity_types.any(ActivityType.id.in_(activity_ids)))
    query = query.filter(Event.end < current_time())
    query = query.order_by(Event.end.desc())

    page = int(flask.request.args.get("page", 1))
    size = int(flask.request.args.get("size", 20))
    paginated = query.paginate(page=page, per_page=size, error_out=False)

    response = RetexEventSchema(many=True).dump(paginated.items)
    return (
        json.dumps({"data": response, "last_page": paginated.pages}),
        200,
        {"content-type": "application/json"},
    )
