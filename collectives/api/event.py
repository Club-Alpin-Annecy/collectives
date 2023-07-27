""" API to get the event list in index page.

"""
import json
from dateutil import parser

from flask import url_for, request, abort
from flask_login import current_user
from marshmallow import fields
from sqlalchemy import desc, or_, func

from collectives.api.common import blueprint, marshmallow, avatar_url
from collectives.models import Event, EventStatus, EventType
from collectives.models import ActivityType, User, EventTag
from collectives.utils.url import slugify


def photo_uri(event):
    """Generate an URI for event image using Flask-Images.

    Returned images are thumbnail of 200x130 px.

    :param event: Event which will be used to get the image.
    :type event: :py:class:`collectives.models.event.Event`
    :return: The URL to the thumbnail
    :rtype: string
    """
    if event.photo is not None:
        return url_for("images.crop", filename=event.photo, width=200, height=130)
    return url_for("static", filename="img/icon/ionicon/md-images.svg")


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

def filter_multiple_activity_types(query, list_of_activity_types):
    """Build a query filtering activity types with OR

    :param query: The original query
    :type query: :py:class:`sqlalchemy.orm.query.Query`
    :param list_of_activity_types: A list of activity_types to be filtered with OR
    :type list_of_activity_types: :py:list(string):
    :return: The query filtered with activity types
    :rtype: :py:class:`sqlalchemy.orm.query.Query`
    """
    activity_types = []
    for (activity_type_name) in list_of_activity_types:
        activity_type = Event.activity_types.any(short=activity_type_name)
        activity_types.append(activity_type)
    
    return query.filter(or_(*activity_types))


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
            "tags",
            "has_free_slots",
            "has_free_waiting_slots",
            "has_free_online_slots",
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
    page = int(request.args.get("page"))
    size = int(request.args.get("size"))

    # Initialize query
    query = Event.query

    # Display pending events only to relevant persons
    query = filter_hidden_events(query)

    # Process all filters.
    # All filter are added as AND
    # TODO need to be refacto for multi-activity filtering
    i = 0
    list_of_activity_types = []
    while f"filters[{i}][field]" in request.args:
        value = request.args.get(f"filters[{i}][value]")
        filter_type = request.args.get(f"filters[{i}][type]")
        field = request.args.get(f"filters[{i}][field]")

        query_filter = None
        if field == "activity_type":
            list_of_activity_types.append(value)
        elif field == "leaders":
            query_filter = Event.leaders.any(
                func.lower(User.first_name + " " + User.last_name).like(f"%{value}%")
            )
        elif field == "title":
            query_filter = Event.title.like(f"%{value}%")
        elif field == "start":
            query_filter = Event.start >= parser.parse(value, dayfirst=True)
        elif field == "end":
            query_filter = Event.end >= parser.parse(value, dayfirst=True)
        elif field == "status":
            value = getattr(EventStatus, value)
            if filter_type == "=":
                query_filter = Event.status == value
            elif filter_type == "!=":
                query_filter = Event.status != value
        elif field == "tags":
            query_filter = Event.tag_refs.any(type=EventTag.get_type_from_short(value))
        elif field == "event_type":
            # pylint: disable=comparison-with-callable
            query = query.filter(EventType.id == Event.event_type_id)
            # pylint: enable=comparison-with-callable
            query_filter = EventType.short == value

        if query_filter is not None:
            query = query.filter(query_filter)
        # Get next filter
        i += 1

    # Apply a OR filter on activity_types to manage several activity_type selection
    if len(list_of_activity_types) > 0:
        query = filter_multiple_activity_types(query, list_of_activity_types)

    # Process first sorter only
    if "sorters[0][field]" in request.args:
        sort_field = request.args.get("sorters[0][field]")
        sort_dir = request.args.get("sorters[0][dir]")
        order = desc(sort_field) if sort_dir == "desc" else sort_field
        query = query.order_by(order)

    query = query.order_by(Event.id)

    paginated_events = query.paginate(page=page, per_page=size, error_out=False)
    data = EventSchema(many=True).dump(paginated_events.items)
    response = {"data": data, "last_page": paginated_events.pages}

    return json.dumps(response), 200, {"content-type": "application/json"}


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
