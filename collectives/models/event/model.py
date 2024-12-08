""" Module for all Event attributes. """

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import validates
from wtforms.validators import InputRequired

from collectives.models.event.enum import EventStatus, EventVisibility
from collectives.models.globals import db
from collectives.utils.misc import truncate

# Reponsables d'une collective (avec droits de modifs sur ladite collective,
#  pas comptés dans le nombre de place
event_leaders = db.Table(
    "event_leaders",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), index=True),
    db.Column("event_id", db.Integer, db.ForeignKey("events.id"), index=True),
)

# Objets (activités) de la collective. Contrainte: Pour chaque activite de la
# collective il doit exister un co-responsable cable de l'encadrer
event_activity_types = db.Table(
    "event_activity_types",
    db.Column(
        "activity_id", db.Integer, db.ForeignKey("activity_types.id"), index=True
    ),
    db.Column("event_id", db.Integer, db.ForeignKey("events.id"), index=True),
)


class EventModelMixin:
    """Part of Event class with all its attributes and related sqlalchemy wizardies.

    Not really meant to be used alone."""

    __tablename__ = "events"

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

    num_slots = db.Column(
        db.Integer,
        nullable=False,
        default="10",
        info={"min": 1, "validators": InputRequired()},
    )
    """Maximum number of user that can register to this event.

    :type: int"""

    num_online_slots = db.Column(
        db.Integer,
        nullable=False,
        default="0",
        info={"min": 0, "validators": InputRequired()},
    )
    """Maximum number of user that can self-register to this event.

    :type: int"""

    num_waiting_list = db.Column(
        db.Integer,
        nullable=False,
        default="0",
        info={"min": 0, "validators": InputRequired()},
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

    visibility = db.Column(
        db.Enum(EventVisibility),
        nullable=False,
        default=EventVisibility.Licensed,
        info={"choices": EventVisibility.choices(), "coerce": EventVisibility.coerce},
    )
    """Visibility of the event (Public, Private...)

    :type: :py:class:`collectives.models.event.EventVisibility`"""

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
    def user_group_id(self):
        """Primary key of the user group to which to restrict registrations

        :type: int"""
        return db.Column(db.Integer, db.ForeignKey("user_groups.id"))

    @declared_attr
    def event_type_id(self):
        """Primary key of the associated event type  (see
        :py:class:`collectives.models.event_type.EventType`)

        :type: int"""
        return db.Column(db.Integer, db.ForeignKey("event_types.id"), default=1)

    @declared_attr
    def _deprecated_parent_event_id(self):
        """[Deprecated] Primary key of the user group to which to restrict registrations

        :type: int"""
        return db.Column("parent_event_id", db.Integer, db.ForeignKey("events.id"))

    @declared_attr
    def leaders(self):
        """Users who lead this event.

        Several users can lead the same event. Leaders do not subscribe to events
        and do not count in slots.

        :type: :py:class:`collectives.models.user.User`"""
        return db.relationship(
            "User",
            secondary=event_leaders,
            lazy="subquery",
            backref=db.backref("led_events", lazy=True, order_by="Event.start"),
        )

    @declared_attr
    def main_leader(self):
        """Main leader of this event.

        :type: :py:class:`collectives.models.user.User`"""
        return db.relationship("User")

    @declared_attr
    def event_type(self):
        """Type of this event.

        :type: :py:class:`collectives.models.event_type.EventType`"""
        return db.relationship("EventType", lazy="subquery")

    @declared_attr
    def activity_types(self):
        """Types of activity of this Event

        :type: :py:class:`collectives.models.activity_type.ActivityType`"""
        return db.relationship(
            "ActivityType",
            secondary=event_activity_types,
            lazy="subquery",
            backref=db.backref("events", lazy=True),
            order_by="asc(ActivityType.id)",
        )

    @declared_attr
    def registrations(self):
        """Users link to this event.

        Registered users are related by this relationship. Please note that refused
        users are still "registered", even though they do not occupy a slot.

        :type: :py:class:`collectives.models.user.User`"""
        return db.relationship(
            "Registration", backref="event", lazy=True, cascade="all, delete-orphan"
        )

    @declared_attr
    def reservations(self):
        """Reservations linked to this event.

        :type: list(:py:class:`collectives.models.reservation.Reservation`)
        """
        return db.relationship(
            "Reservation",
            back_populates="event",
        )

    @declared_attr
    def payment_items(self):
        """List of payment items associated to this event.

        :type: list(:py:class:`collectives.models.payment.PaymentItem`)
        """
        return db.relationship(
            "PaymentItem", backref="event", lazy=True, cascade="all, delete-orphan"
        )

    @declared_attr
    def tag_refs(self):
        """List of tags associated to this event.

        :type: list(:py:class:`collectives.models.event_tag.EventTag`)
        """
        return db.relationship(
            "EventTag", backref="event", lazy=True, cascade="all, delete-orphan"
        )

    @declared_attr
    def questions(self):
        """List of questions associated to this event

        :type: list(:py:class:`collectives.models.question.Question`)
        """
        return db.relationship(
            "Question",
            backref="event",
            lazy=True,
            cascade="all, delete-orphan",
            order_by="Question.order",
        )

    @declared_attr
    def _user_group(self):
        """User Group

        Registrations to this event will we limited to users that are members of this group

        :type: :py:class:`collectives.models.event.Event`
        """
        return db.relationship(
            "UserGroup",
            foreign_keys="Event.user_group_id",
            single_parent=True,
            lazy=True,
            cascade="all, delete-orphan",
            backref="event",
        )

    @property
    def user_group(self):
        """Overload user_group property access to automatically perform migration
        :return: :py:class:`sqlalchemy.orm.relationship`
        """
        # Migrate to new version of attribute
        if self._user_group is None:
            self._migrate_parent_event_id()
        return self._user_group

    @user_group.setter
    def user_group(self, value):
        """Overloaded setter for user_group"""
        self._user_group = value

    @validates("title")
    def truncate_string(self, key, value):
        """Truncates a string to the max SQL field length
        :param string key: name of field to validate
        :param string value: tentative value
        :return: Truncated string.
        :rtype: string
        """
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        return truncate(value, max_len)

    @property
    def tags(self):
        """Direct list of the tag types of this event."""
        return [t.full for t in self.tag_refs]

    id = db.Column(db.Integer, primary_key=True)
