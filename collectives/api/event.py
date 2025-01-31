"""API to get the event list in index page."""

import json

from flask import url_for, request, abort
from flask_login import current_user
from marshmallow import fields
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import selectinload, joinedload

from collectives.api.common import blueprint, marshmallow, avatar_url
from collectives.models import db, Event, EventStatus, EventType, EventVisibility
from collectives.models import ActivityType, User, EventTag
from collectives.models import Question, QuestionAnswer
from collectives.utils.url import slugify
from collectives.utils.access import valid_user
from collectives.utils.time import format_datetime_range, parse_api_date


def photo_uri(event):
    """Generate an URI for event image using Flask-Images.

    Returned images are thumbnail of 200x130 px.

    :param event: Event which will be used to get the image.
    :type event: :py:class:`collectives.models.event.Event`
    :return: The URL to the thumbnail
    :rtype: string
    """
    if event.photo is not None:
        return url_for("images.crop", filename=event.photo, width=350, height=250)
    return url_for("static", filename=f"img/default/events/event{event.id%8 + 1}.svg")


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


class UserSimpleSchema(marshmallow.Schema):
    """Schema used to describe leaders in event list"""

    avatar_uri = fields.Function(avatar_url)
    """ Profile picture URI of the user.

    :type: string"""
    name = fields.Function(lambda user: user.full_name())
    """ User full name.

    :type: string"""

    class Meta:
        """Fields to expose"""

        fields = ("id", "name", "avatar_uri")


class ActivityTypeSchema(marshmallow.Schema):
    """Schema to describe activity types"""

    class Meta:
        """Fields to expose"""

        fields = ("id", "short", "name")


class EventTypeSchema(marshmallow.Schema):
    """Schema to describe event types"""

    class Meta:
        """Fields to expose"""

        fields = ("id", "short", "name")


class EventSchema(marshmallow.Schema):
    """Schema used to describe event in index page."""

    photo_uri = fields.Function(photo_uri)
    """ URI of the event image thumnail.

    See also: :py:func:`photo_uri`

    :type: :py:class:`marshmallow.fields.Function`"""
    free_slots = fields.Function(lambda event: event.free_slots())
    """ Number of free user slots for this event.

    :type: :py:class:`marshmallow.fields.Function` """
    occupied_slots = fields.Function(
        lambda event: len(event.holding_slot_registrations())
    )
    """ Number of occupied user slots for this event.

    :type: :py:class:`marshmallow.fields.Function`"""
    leaders = fields.Function(
        lambda event: UserSimpleSchema(many=True).dump(event.ranked_leaders())
    )
    """ Information about event leaders in JSON.

    See also: :py:class:`UserSimpleSchema`

    :type: :py:class:`marshmallow.fields.Function`"""
    event_types = fields.Function(
        lambda event: EventTypeSchema(many=True).dump([event.event_type])
    )
    """ Type of event.
    Note: this is a list so that the frontend code can be shared with activity types / tags.
    Only one value is ever expected.

    :type: :py:class:`marshmallow.fields.Function`"""
    activity_types = fields.Function(
        lambda event: ActivityTypeSchema(many=True).dump(event.activity_types)
    )
    """ Types of activity of this event.

    :type: :py:class:`marshmallow.fields.Function`"""
    view_uri = fields.Function(
        lambda event: url_for(
            "event.view_event", event_id=event.id, name=slugify(event.title)
        )
    )
    """ URI to the event page.

    :type: :py:class:`marshmallow.fields.Function`"""

    is_confirmed = fields.Function(lambda event: event.is_confirmed())
    """ Current event status is confirmed.

    :type: :py:class:`marshmallow.fields.Function`"""
    tags = fields.Function(lambda event: event.tags)
    """ Tags this event.

    :type: :py:class:`marshmallow.fields.Function`"""
    has_free_slots = fields.Function(lambda event: event.has_free_slots())
    """ Tags this event.

    :type: :py:class:`marshmallow.fields.Function`"""
    has_free_waiting_slots = fields.Function(
        lambda event: event.has_free_waiting_slots()
    )
    """ Tags this event.

     :type: :py:class:`marshmallow.fields.Function`"""
    has_free_online_slots = fields.Function(lambda event: event.has_free_online_slots())
    """ Tags this event.

    :type: :py:class:`marshmallow.fields.Function`"""

    formated_datetime_range = fields.Function(
        lambda event: format_datetime_range(event.start, event.end)
    )

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "title",
            "start",
            "end",
            "num_slots",
            "num_online_slots",
            "registration_open_time",
            "registration_close_time",
            "photo_uri",
            "view_uri",
            "free_slots",
            "occupied_slots",
            "leaders",
            "activity_types",
            "event_types",
            "is_confirmed",
            "status",
            "visibility",
            "tags",
            "has_free_slots",
            "has_free_waiting_slots",
            "has_free_online_slots",
            "formated_datetime_range",
        )


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
                *map(
                    lambda type: Event.activity_types.any(short=type),
                    filters_activity_types,
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


class AutocompleteEventSchema(marshmallow.Schema):
    """Schema under which autocomplete suggestions are returned"""

    view_uri = fields.Function(
        lambda event: url_for(
            "event.view_event", event_id=event.id, name=slugify(event.title)
        )
    )
    """ URI to the event page.

    :type: :py:class:`marshmallow.fields.Function`"""

    class Meta:
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


class QuestionAnswerSchema(marshmallow.Schema):
    """Schema according to which question answers are returned"""

    delete_uri = fields.Function(
        lambda answer: url_for("question.delete_answer", answer_id=answer.id)
    )
    """ URI for deleting the answer.

    :type: :py:class:`marshmallow.fields.Function`"""

    author_name = fields.Function(lambda answer: answer.user.full_name())

    question_title = fields.Function(lambda answer: answer.question.title)

    registration_status = fields.Function(_get_answer_registration_status)

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "value",
            "author_name",
            "question_title",
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
