""" API to get the event list in index page.

"""
import json
from flask import url_for, request
from sqlalchemy import desc, func
from marshmallow import fields

from ..models import Event, EventStatus, User
from ..utils.url import slugify
from ..utils.event import filter_hidden_events
from ..utils.time import current_time
from .common import blueprint, marshmallow, avatar_url


class UserSimpleSchema(marshmallow.Schema):
    """ Schema used to describe leaders in event list """

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
    """ Schema to describe activity types """

    class Meta:
        """Fields to expose"""

        fields = ("id", "short", "name")


class EventSchema(marshmallow.Schema):
    """ Schema used to describe event in index page."""

    free_slots = fields.Function(lambda event: event.free_slots())
    """ Number of free user slots for this event.

    :type: :py:class:`marshmallow.fields.Function` """
    occupied_slots = fields.Function(lambda event: len(event.active_registrations()))
    """ Number of occupied user slots for this event.

    :type: :py:class:`marshmallow.fields.Function`"""
    leaders = fields.Function(
        lambda event: UserSimpleSchema(many=True).dump(event.ranked_leaders())
    )
    """ Information about event leaders in JSON.

    See also: :py:class:`UserSimpleSchema`

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
    status = fields.Function(lambda event: event.status_string())
    """ Current status event.

    :type: :py:class:`marshmallow.fields.Function`"""
    tags = fields.Function(lambda event: event.tags)
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
            "photo_thumbnail",
            "view_uri",
            "free_slots",
            "occupied_slots",
            "leaders",
            "activity_types",
            "is_confirmed",
            "status",
            "tags",
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
    i = 0
    while f"filters[{i}][field]" in request.args:
        value = request.args.get(f"filters[{i}][value]")
        filter_type = request.args.get(f"filters[{i}][type]")
        field = request.args.get(f"filters[{i}][field]")

        if field == "status":
            value = getattr(EventStatus, value)

        query_filter = None
        if field == "activity_type":
            query_filter = Event.activity_types.any(short=value)
        if field == "leaders":
            query_filter = Event.leaders.any(
                func.lower(User.first_name + " " + User.last_name).like(f"%{value}%")
            )
        if field == "title":
            query_filter = Event.title.like(f"%{value}%")
        elif field == "end":
            if filter_type == ">=":
                query_filter = Event.end >= current_time().date()
        elif field == "status":
            if filter_type == "=":
                query_filter = Event.status == value
            elif filter_type == "!=":
                query_filter = Event.status != value

        if query_filter is not None:
            query = query.filter(query_filter)
        # Get next filter
        i += 1

    # Process first sorter only
    if "sorters[0][field]" in request.args:
        sort_field = request.args.get("sorters[0][field]")
        sort_dir = request.args.get("sorters[0][dir]")
        order = desc(sort_field) if sort_dir == "desc" else sort_field
        query = query.order_by(order)

    query = query.order_by(Event.id)

    paginated_events = query.paginate(page, size, False)
    data = EventSchema(many=True).dump(paginated_events.items)
    response = {"data": data, "last_page": paginated_events.pages}

    return json.dumps(response), 200, {"content-type": "application/json"}
