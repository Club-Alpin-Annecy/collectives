"""API to get the event list in index page."""

import json
from datetime import timedelta

from flask import abort, request, url_for
from flask_login import current_user
from marshmallow import fields
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload, selectinload

from collectives.api.common import blueprint, marshmallow
from collectives.api.schemas import EventSchema, UserSchema
from collectives.models import (
    ActivityKind,
    ActivityType,
    Configuration,
    Event,
    EventStatus,
    EventTag,
    EventType,
    EventVisibility,
    Question,
    QuestionAnswer,
    User,
    db,
)
from collectives.utils.access import valid_user
from collectives.utils.time import current_time, parse_api_date


def filter_hidden_events(query):
    """Update a SQLAlchemy query object with a filter that
    removes Event with a status that the current use is not allowed to see

     - Moderators can see all events
     - Normal users cannot see 'Pending' events
     - Activity supervisors can see 'Pending' events for the activities that
       they supervise
     - Leaders can see the events that they lead
     - Users with role for an activity can see 'Activity' events
     - Users with any role can see 'Activity' events without activities

    :param query: The original query
    :type query: :py:class:`sqlalchemy.orm.query.Query`
    :return: The filtered query
    :rtype: :py:class:`sqlalchemy.orm.query.Query`
    """
    # Display pending/private events only to relevant persons
    if not current_user.is_authenticated:
        # Not logged users see no pending/private event
        query = query.filter(Event.status != EventStatus.Pending)
        query = query.filter(Event.visibility != EventVisibility.Activity)
    elif current_user.is_moderator():
        # Admin see all pending/private events (no filter)
        pass
    else:
        # Regular user can see no Pending
        status_query_filter = Event.status != EventStatus.Pending

        # If user is a supervisor, it can see Pending events of its activities
        if current_user.is_supervisor():
            # Supervisors can see all sup
            activities = current_user.get_supervised_activities()
            activities_ids = [a.id for a in activities]
            activity_filter = Event.activity_types.any(
                ActivityType.id.in_(activities_ids)
            )
            status_query_filter = or_(status_query_filter, activity_filter)

        # Users can only see Activity events for their activities
        vis_query_filter = Event.visibility != EventVisibility.Activity
        activities = current_user.activities_with_role()
        if activities:
            activities_ids = [a.id for a in activities]
            activity_filter = Event.activity_types.any(
                ActivityType.id.in_(activities_ids)
            )
            vis_query_filter = or_(vis_query_filter, activity_filter)
        # Special case for Activity events without activities: all user with roles can see them
        if current_user.has_any_role():
            vis_query_filter = or_(vis_query_filter, ~Event.activity_types.any())

        # If user can create event, they can see all events they lead
        query_filter = and_(status_query_filter, vis_query_filter)
        if current_user.can_create_events():
            lead = Event.leaders.any(id=current_user.id)
            query_filter = or_(query_filter, lead)

        # After filter construction, it is applied to the query
        query = query.filter(query_filter)

    return query


@blueprint.route("/events/")
def events():
    """API endpoint to list events.

    It can be filtered using tabulator filter and sorter. It is paginated using
    ``page`` and ``size`` GET parameters. Regular users cannot see `Pending` event.

    :return: A tuple:

        - JSON containing information describe in EventSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    page = int(request.args.get("page", 0))
    size = int(request.args.get("size", 25))

    # Initialize query
    query = db.session.query(Event)
    query = query.options(
        selectinload(Event.tag_refs), selectinload(Event.registrations)
    )

    # Hide very old events to unauthenticated
    if not current_user.is_authenticated:
        min_date = current_time() - timedelta(
            days=Configuration.MAX_HISTORY_FOR_ANONYMOUS
        )
        query = query.filter(Event.end > min_date)

    # Display pending events only to relevant persons
    query = filter_hidden_events(query)

    # Process all filters.
    # All filter are added as AND
    i = 0
    filters_activity_types = []
    filters_tags = []
    filters_types = []
    while f"filters[{i}][field]" in request.args:
        value = request.args.get(f"filters[{i}][value]")
        filter_type = request.args.get(f"filters[{i}][type]")
        field = request.args.get(f"filters[{i}][field]")

        query_filter = None
        if field == "activity_type":
            filters_activity_types.append(value)
        elif field == "tags":
            filters_tags.append(EventTag.get_type_from_short(value))
        elif field == "event_type":
            filters_types.append(value)
        elif field == "leaders":
            query_filter = Event.leaders.any(
                func.lower(User.first_name + " " + User.last_name).like(f"%{value}%")
            )
        elif field == "title":
            query_filter = Event.title.like(f"%{value}%")
        elif field == "start":
            value = parse_api_date(value)
            if value is not None:
                query_filter = Event.start >= value
        elif field == "end":
            value = parse_api_date(value)
            if value is not None:
                query_filter = Event.end >= value
        elif field == "status":
            value = getattr(EventStatus, value)
            if filter_type == "=":
                query_filter = Event.status == value
            elif filter_type == "!=":
                query_filter = Event.status != value

        if query_filter is not None:
            query = query.filter(query_filter)
        # Get next filter
        i += 1

    # Apply a OR filter on activity_types to manage several activity_type selection
    if len(filters_activity_types) > 0:
        query = query.filter(
            or_(
                *(
                    (
                        Event.activity_types.any(kind=ActivityKind.Service)
                        if type == "__services"
                        else Event.activity_types.any(short=type)
                    )
                    for type in filters_activity_types
                )
            )
        )

    # Add query filter from filters_tag list
    if len(filters_tags) > 0:
        query = query.filter(
            or_(*map(lambda tag: Event.tag_refs.any(type=tag), filters_tags))
        )

    # Add query filter from filters_types list
    if len(filters_types) > 0:
        # pylint: disable=comparison-with-callable
        query = query.filter(EventType.id == Event.event_type_id)
        # pylint: enable=comparison-with-callable
        query = query.filter(
            or_(*map(lambda type: EventType.short == type, filters_types))
        )

    query = query.order_by(Event.start)
    query = query.order_by(Event.id)

    paginated_events = query.paginate(page=page, per_page=size, error_out=False)
    data = EventSchema(many=True).dump(paginated_events.items)

    return (
        json.dumps(
            {
                "data": data,
                "last_page": paginated_events.pages,
                "total": paginated_events.total,
            }
        ),
        200,
        {"content-type": "application/json", "Access-Control-Allow-Origin": "*"},
    )


class AutocompleteEventSchema(EventSchema):
    """Schema under which autocomplete suggestions are returned"""

    class Meta(EventSchema.Meta):
        """Fields to expose"""

        fields = ("id", "title", "start", "view_uri")


@blueprint.route("/event/autocomplete/")
def autocomplete_event():
    """API endpoint for event autocompletion.

    At least 2 characters are required to make a name search.

    :param string q: Search string. Either the event id or a substring from the title
    :param int l: Maximum number of returned items.
    :param list[int] aid: List of activity ids to include. Empty means include
                          events for any activity
    :param list[int] eid: List of event ids to exclude
    :return: A tuple:

        - JSON containing information describe in AutocompleteUserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """

    found_events = []

    search_term = request.args.get("q")
    if not search_term:
        abort(400)

    try:
        event_id = int(search_term)
    except ValueError:
        event_id = None

    if event_id is not None or (len(search_term) >= 2):
        limit = request.args.get("l", type=int) or 8
        activity_ids = request.args.getlist("aid", type=int)
        excluded_ids = request.args.getlist("eid", type=int)

        query = Event.query

        # Search term in title or id
        search_clause = Event.title.ilike(f"%{search_term}%")
        if event_id:
            search_clause = or_(search_clause, (Event.id == event_id))
        query = query.filter(search_clause)

        # Remove excluded ids
        query = query.filter(~Event.id.in_(excluded_ids))

        query_without_activity_filtering = query

        # Restrict to event with one of the provided activities
        if activity_ids:
            query = query.filter(
                Event.activity_types.any(ActivityType.id.in_(activity_ids))
            )

        query = query.order_by(Event.id.desc())
        found_events = query.limit(limit).all()

        if len(found_events) < limit:
            # We haven't found enough events, try without activity filtering,
            # See issue #618
            query = query_without_activity_filtering
            query = query.filter(~Event.id.in_([event.id for event in found_events]))
            query = query.order_by(Event.id.desc())
            found_events += query.limit(limit - len(found_events)).all()

    content = AutocompleteEventSchema().dumps(found_events, many=True)
    return content, 200, {"content-type": "application/json"}


def _get_answer_registration_status(answer: QuestionAnswer) -> str:
    """:returns: the string corresponding to the registration status of the user
    that authored an answer"""

    reg = next(iter(answer.question.event.existing_registrations(answer.user)), None)
    return reg.status.display_name() if reg else "Supprimée"


class QuestionSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema according to which question are returned"""

    class Meta:
        """Fields to expose"""

        model = Question


class QuestionAnswerSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema according to which question answers are returned"""

    delete_uri = fields.Function(
        lambda answer: url_for("question.delete_answer", answer_id=answer.id)
    )
    """ URI for deleting the answer.

    :type: :py:class:`marshmallow.fields.Function`"""

    user = fields.Nested(UserSchema, only=("full_name",))
    question = fields.Nested(QuestionSchema, only=("title",))

    registration_status = fields.Function(_get_answer_registration_status)

    class Meta:
        """Fields to expose"""

        model = QuestionAnswer
        include_relationships = True
        fields = (
            "id",
            "value",
            "user",
            "question",
            "delete_uri",
            "registration_status",
        )


@blueprint.route("/event/<int:event_id>/answers/")
@valid_user()
def event_question_answers(event_id: int):
    """API endpoint for listing answers to an event's questions

    :param event_id: Id of the event
    """
    event = db.session.get(Event, event_id)
    if event is None:
        return abort(404)

    if not event.has_edit_rights(current_user):
        return abort(403)

    query = db.session.query(QuestionAnswer)
    query = query.options(
        joinedload(QuestionAnswer.question)
        .selectinload(Question.event)
        .joinedload(Event.registrations),
        selectinload(QuestionAnswer.user),
    )
    query = (
        query.filter(QuestionAnswer.question_id == Question.id)
        .filter(Question.event_id == event_id)
        .order_by(Question.order)
    )
    answers = query.all()

    content = QuestionAnswerSchema().dumps(answers, many=True)

    return content, 200, {"content-type": "application/json"}
