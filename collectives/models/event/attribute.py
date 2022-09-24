""" Module for all Event attributes. """

from sqlalchemy.ext.declarative import declared_attr
from collectives.models.globals import db
from collectives.models.event.status import EventStatus


class AttributeEvent:
    """Part of Event class with all its attributes.

    Not meant to be used alone."""

    id = db.Column(db.Integer, primary_key=True)
    """Event unique id.

    ID used as DB primary key, and in most URL such as /event/<id>

    :type: int
    """

    title = db.Column(db.String(100), nullable=False)
    """Title of the event.

    Title will be displayed in event list and in top of event detail page.

    :type: string"""

    description = db.Column(db.Text(), nullable=False, default="")
    """Raw event description as markdown text.

    :type: string"""

    rendered_description = db.Column(db.Text(), nullable=True, default="")
    """Rendered event description as HTML.

    :type: string"""

    photo = db.Column(db.String(100), nullable=True)
    """Path to event photo in UploadSet

    :type: string"""

    start = db.Column(db.DateTime, nullable=False, index=True)
    """Start of event.

    :type: :py:class:`datetime.datetime`"""

    end = db.Column(db.DateTime, nullable=False)
    """End of event.

    :type: :py:class:`datetime.datetime`"""

    num_slots = db.Column(db.Integer, nullable=False, default="10", info={"min": 1})
    """Maximum number of user that can register to this event.

    :type: int"""

    num_online_slots = db.Column(
        db.Integer, nullable=False, default="0", info={"min": 0}
    )
    """Maximum number of user that can self-register to this event.

    :type: int"""

    num_waiting_list = db.Column(
        db.Integer, nullable=False, default="0", info={"min": 0}
    )
    """Maximum number of user that can queue for this event.

    :type: int"""

    registration_open_time = db.Column(db.DateTime, nullable=True)
    """Earliest moment an user can self-register to this event.

    This attribute can be ``null`` if event has no online slots.

    :type: :py:class:`datetime.datetime`"""

    registration_close_time = db.Column(db.DateTime, nullable=True)
    """Latest moment an user can self-register to this event.

    This attribute can be ``null`` if event has no online slots.

    :type: :py:class:`datetime.datetime`"""

    status = db.Column(
        db.Enum(EventStatus),
        nullable=False,
        default=EventStatus.Confirmed,
        info={"choices": EventStatus.choices(), "coerce": EventStatus.coerce},
    )
    """Status of the event (Confirmed, Cancelled...)

    :type: :py:class:`collectives.models.event.EventStatus`"""

    # Non DB attributes
    @property
    def activity_type_names(self):
        """
        :return: A string of the actitivities names of the event
        :rtype: string"""
        return " - ".join([a.name for a in self.activity_types])

    # For ForeignKey Mixin, we have to use a function and declared_attr, but it is the same as
    # declaring an attribute. Cf
    # https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/mixins.html#mixing-in-columns

    @declared_attr
    def main_leader_id(self):
        """Primary key of the registered user (see  :py:class:`collectives.models.user.User`)

        :type: int"""
        return db.Column(db.Integer, db.ForeignKey("users.id"))

    @declared_attr
    def parent_event_id(self):
        """Primary key of the parent curriculum event

        :type: int"""
        return db.Column(db.Integer, db.ForeignKey("events.id"))

    @declared_attr
    def event_type_id(self):
        """Primary key of the associated event type  (see
        :py:class:`collectives.models.eventtype.EventType`)

        :type: int"""
        return db.Column(db.Integer, db.ForeignKey("event_types.id"), default=1)
