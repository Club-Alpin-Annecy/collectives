"""Module with various tools to filter event.
"""
from flask_login import current_user
from sqlalchemy import or_

from ..models import Event, EventStatus, ActivityType


def filter_hidden_events(query):
    """Update a SQLAlchemy query object with a filter that
    removes Event with a status that the current use is not allowed to see

     - Moderators can see all events
     - Normal users cannot see 'Pending' events
     - Activity supervisors can see 'Pending' events for the activities that
       they supervise
     - Leaders can see the events that they lead

    :param query: The original query
    :type query: :py:class:`sqlalchemy.orm.query.Query`
    :return: The filtered query
    :rtype: :py:class:`sqlalchemy.orm.query.Query`
    """
    # Display pending events only to relevant persons
    if not current_user.is_authenticated:
        # Not logged users see no pending event
        query = query.filter(Event.status != EventStatus.Pending)
    elif current_user.is_moderator():
        # Admin see all pending events (no filter)
        pass
    else:
        # Regular user can see non Pending
        query_filter = Event.status != EventStatus.Pending

        # If user is a supervisor, it can see Pending events of its activities
        if current_user.is_supervisor():
            # Supervisors can see all sup
            activities = current_user.get_supervised_activities()
            activities_ids = [a.id for a in activities]
            supervised = Event.activity_types.any(ActivityType.id.in_(activities_ids))
            query_filter = or_(query_filter, supervised)

        # If user can create event, it can see its pending events
        if current_user.can_create_events():
            lead = Event.leaders.any(id=current_user.id)
            query_filter = or_(query_filter, lead)

        # After filter construction, it is applied to the query
        query = query.filter(query_filter)
    return query
