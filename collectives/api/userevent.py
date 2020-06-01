""" API used to get events linked to a user for profiles.

Event schema is the one from :py:class:`collectives.api.event.EventSchema`
"""
import json

from flask_login import current_user, login_required

from ..models import db, User, Event
from ..models import Registration, RegistrationStatus

from .common import blueprint
from .event import EventSchema, filter_hidden_events


@blueprint.route("/user/<user_id>/events")
@login_required
def user_events(user_id):
    """ Get all event of a user.

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
    query = filter_hidden_events(query)

    query = query.filter(Registration.user_id == user_id)
    query = query.filter(Registration.status == RegistrationStatus.Active)
    query = query.filter(Event.id == Registration.event_id)
    query = query.order_by(Event.start, Event.id)

    result = query.all()
    response = EventSchema(many=True).dump(result)

    return json.dumps(response), 200, {"content-type": "application/json"}


# Get all lead events of a leader
@blueprint.route("/leader/<leader_id>/events")
@login_required
def leader_events(leader_id):
    """ Get all event of a leader.

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
    query = filter_hidden_events(query)

    query = query.filter(Event.leaders.contains(leader))
    query = query.order_by(Event.start, Event.id)

    result = query.all()
    response = EventSchema(many=True).dump(result)

    return json.dumps(response), 200, {"content-type": "application/json"}
