"""Module defining frequently used marshmallow schemas"""

from marshmallow import fields

from flask import url_for

from collectives.utils.url import slugify
from collectives.api.common import marshmallow, avatar_url
from collectives.models import Event, EventType, Role, Badge
from collectives.models import ActivityType, User, EventTag
from collectives.utils.time import format_datetime_range


class ActivityTypeSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema to describe activity types"""

    class Meta:
        """Fields to expose"""

        model = ActivityType
        fields = ("id", "short", "name", "kind")


class RoleSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema for the role of a user.

    Mainly used in :py:attr:`UserSchema.roles`
    """

    name = fields.Str()

    activity_type = fields.Nested(ActivityTypeSchema, only=["name", "short"])

    class Meta:
        """Fields to expose"""

        model = Role
        include_relationships = True
        fields = (
            "name",
            "role_id",
            "activity_type",
        )


class BadgeSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema for the badges of a user.

    Mainly used in :py:attr:`UserSchema.badges`
    """

    name = fields.Str()

    activity_type = fields.Nested(ActivityTypeSchema, only=["name"])

    class Meta:
        """Fields to expose"""

        model = Badge
        include_relationships = True
        fields = (
            "name",
            "badge_id",
            "activity_type",
            "expiration_date",
            "level",
        )


class UserSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema of a user to be used to extract API information.

    This class is a ``marshmallow`` schema which automatically gets its
    structure from the ``User`` class. Plus, we add some useful information
    or link. This schema is only used for administration listing.
    """

    profile_uri = fields.Function(
        lambda user: url_for("profile.show_user", user_id=user.id)
    )
    """ URI to see user profile

    :type: string
    """
    leader_profile_uri = fields.Function(
        lambda user: (
            url_for("profile.show_leader", leader_id=user.id)
            if user.can_create_events()
            else None
        )
    )
    """ URI to see user profile

    :type: string
    """
    avatar_uri = fields.Function(avatar_url)
    """ URI to a resized version (30px) of user avatar

    :type: string
    """

    full_name = fields.Function(lambda user: user.full_name())
    """ User full name

    :type: string"""

    roles = fields.Nested(RoleSchema, many=True)
    """ List of roles of the User.

    :type: list(dict())"""

    badges = fields.Nested(BadgeSchema, many=True)
    """ List of badges of the User.

    :type: list(dict())"""

    is_active = fields.Boolean()

    class Meta:
        """Fields to expose"""

        model = User
        include_relationships = True
        fields = (
            "id",
            "mail",
            "is_active",
            "enabled",
            "avatar_uri",
            "first_name",
            "last_name",
            "roles",
            "badges",
            "profile_uri",
            "leader_profile_uri",
            "full_name",
        )


class EventTypeSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema to describe event types"""

    class Meta:
        """Fields to expose"""

        model = EventType
        fields = ("id", "short", "name")


class EventTagSchema(marshmallow.SQLAlchemyAutoSchema):
    """Schema to describe event tags"""

    name = fields.Str()
    short = fields.Str()

    class Meta:
        """Fields to expose"""

        model = EventTag
        fields = ("id", "short", "name")


def photo_uri(event):
    """Generate an URI for event image using Flask-Images.

    Returned images are thumbnail of 350x250 px.

    :param event: Event which will be used to get the image.
    :type event: :py:class:`collectives.models.event.Event`
    :return: The URL to the thumbnail
    :rtype: string
    """
    if event.photo is not None:
        return url_for("images.crop", filename=event.photo, width=350, height=250)
    return url_for("static", filename=f"img/default/events/event{event.id%8 + 1}.svg")


class EventSchema(marshmallow.SQLAlchemyAutoSchema):
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
    leaders = fields.Nested(
        UserSchema, only=("id", "full_name", "avatar_uri"), many=True
    )
    """ Information about event leaders in JSON.

    See also: :py:class:`UserSimpleSchema`

    :type: :py:class:`marshmallow.fields.Function`"""

    event_type = fields.Nested(EventTypeSchema)
    """ Type of event.

    :type: :py:class:`marshmallow.fields.Function`"""
    activity_types = fields.Nested(ActivityTypeSchema, many=True)
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
    tags = fields.Nested(EventTagSchema, many=True)
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

    activity_type_names = fields.Str()

    status = fields.Function(lambda event: event.status.value)
    """Status of the event, as an int for backward compatibility"""

    visibility = fields.Function(lambda event: event.visibility.value)
    """Visibility of the event, as an int for backward compatibility"""

    class Meta:
        """Fields to expose"""

        model = Event
        include_relationships = True
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
            "activity_type_names",
            "event_type",
            "is_confirmed",
            "status",
            "visibility",
            "tags",
            "has_free_slots",
            "has_free_waiting_slots",
            "has_free_online_slots",
            "formated_datetime_range",
        )
