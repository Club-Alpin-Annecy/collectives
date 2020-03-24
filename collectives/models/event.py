"""Module for event related classes
"""
import re
import markdown
from flask_uploads import UploadSet, IMAGES

from .globals import db
from .registration import RegistrationStatus
from .utils import ChoiceEnum

photos = UploadSet("photos", IMAGES)
"""Upload instance for events photos

:type: flask_uploads.UploadSet"""


class EventStatus(ChoiceEnum):
    """ Enum listing status of an event"""

    Confirmed = 0
    """Confirmed event"""
    Pending = 1
    """Pending event

    A pending event is not visible from most users"""
    Cancelled = 2
    """Cancelled event"""

    @classmethod
    def display_names(cls):
        """Display name of the current status

        :return: status of the event
        :rtype: string
        """
        return {
            cls.Confirmed: "Confirmée",
            cls.Pending: "En attente",
            cls.Cancelled: "Annulée",
        }


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


class Event(db.Model):
    """ Class of an event.

    An event is an object a a determined start and end, related to
    actitivity types, leaders and user subscriptions. Description are stored
    as markdown format and html format.
    """

    __tablename__ = "events"

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

    :type: datetime.datetime"""

    end = db.Column(db.DateTime, nullable=False)
    """End of event.

    :type: datetime.datetime"""

    num_slots = db.Column(db.Integer, nullable=False, default="10", info={"min": 1})
    """Maximum number of user that can register to this event.

    :type: int"""

    num_online_slots = db.Column(
        db.Integer, nullable=False, default="0", info={"min": 0}
    )
    """Maximum number of user that can self-register to this event.

    :type: int"""

    registration_open_time = db.Column(db.DateTime, nullable=True)
    """Earliest moment an user can self-register to this event.

    This attribute can be ``null`` if event has no online slots.

    :type: datetime.datetime"""

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

    # Relationships
    leaders = db.relationship(
        "User",
        secondary=event_leaders,
        lazy="subquery",
        backref=db.backref("led_events", lazy=True, order_by="Event.start"),
    )
    """Users who lead this event.

    Several users can lead the same event. Leaders do not subscribe to events
    and do not count in slots.

    :type: :py:class:`collectives.models.user.User`"""

    activity_types = db.relationship(
        "ActivityType",
        secondary=event_activity_types,
        lazy="subquery",
        backref=db.backref("events", lazy=True),
    )
    """Types of activity of this Event

    :type: :py:class:`collectives.models.activitytype.ActivityType`"""

    registrations = db.relationship(
        "Registration", backref="event", lazy=True, cascade="all, delete-orphan"
    )
    """Users link to this event.

    Registered users are related by this relationship. Please note that refused
    users are still "registered", even though they do not occupy a slot.

    :type: :py:class:`collectives.models.user.User`"""

    def save_photo(self, file):
        """Save event photo from a raw file

        Process a raw form data field to add it to the Event as the event
        photo. If ``file`` is None (ie data is empty, no file was submitted),
        do nothing.

        :param file:
        :type file: :py:class:`werkzeug.datastructures.FileStorage`
        """
        if file is not None:
            filename = photos.save(file, name="event-" + str(self.id) + ".")
            self.photo = filename

    def set_rendered_description(self, description):
        """Render description and returns it.

        :param description: Markdown description.
        :type description: string
        :return: Rendered description as HTML
        :rtype: string
        """
        # Urify links
        # From https://daringfireball.net/2010/07/improved_regex_for_matching_urls
        # pylint: disable=C0301
        URI_REGEX = r'(?i)(^|^\s|[^(]\s+|[^\]]\(\s*)((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'
        description = re.sub(URI_REGEX, r"\1[\2](\2)", description)
        self.rendered_description = markdown.markdown(description, extensions=["nl2br"])
        return self.rendered_description

    # Date validation
    def has_defined_registration_date(self):
        # One should not creat an event with online slot defined but
        # any registration dates (open and close)
        if not self.registration_open_time or not self.registration_close_time:
            return False
        return True

    def starts_before_ends(self):
        # Event must starts before it ends
        return self.start <= self.end

    def opens_before_closes(self):
        # Registrations must open before they close
        return self.registration_open_time <= self.registration_close_time

    def opens_before_ends(self):
        # Registrations must open before event ends
        return self.registration_open_time <= self.end

    def has_valid_slots(self):
        # pylint: disable=C0301
        return self.num_online_slots >= 0 and self.num_slots >= self.num_online_slots

    def has_valid_leaders(self):
        if not any(self.activity_types):
            return False
        for activity in self.activity_types:
            if not activity.can_be_led_by(self.leaders):
                return False
        return True

    def is_valid(self):
        # Do not test registration date if online slots is null. Registration
        # date is meant to be used only by an online user while registering.
        # The leader or administrater is always able to register someone even if
        # registration date are closed.
        if self.num_online_slots == 0:
            return (
                self.starts_before_ends()
                and self.has_valid_slots()
                and self.has_valid_leaders()
            )

        return (
            self.starts_before_ends()
            and self.has_valid_slots()
            and self.has_valid_leaders()
            and self.starts_before_ends()
            and self.opens_before_closes()
            and self.has_defined_registration_date()
        )

    def is_leader(self, user):
        return user in self.leaders

    def is_supervisor(self, user):
        return any([a for a in self.activity_types if user.supervises_activity(a.id)])

    def has_edit_rights(self, user):
        """
        Returns true if either:
         - user is leader of this event
         - user supervises any of this event activities
         - user is moderator
        """
        if user.is_moderator():
            return True
        return self.is_leader(user) or self.is_supervisor(user)

    def has_delete_rights(self, user):
        """
        Returns true if either:
         - user supervises any of this event activities
         - user is moderator
        """
        return user.is_moderator() or self.is_supervisor(user)

    # Registrations

    def is_registration_open_at_time(self, time):
        return self.registration_open_time <= time <= self.registration_close_time

    def active_registrations(self):
        return [
            registration
            for registration in self.registrations
            if registration.is_active()
        ]

    def has_free_slots(self):
        return len(self.active_registrations()) < self.num_slots

    def has_free_online_slots(self):
        return len(self.active_registrations()) < self.num_online_slots

    def free_slots(self):
        free = self.num_slots - len(self.active_registrations())
        return 0 if free < 0 else free

    def is_registered(self, user):
        existing_registrations = [
            registration
            for registration in self.registrations
            if registration.user_id == user.id
        ]
        return any(existing_registrations)

    def is_registered_with_status(self, user, statuses):
        existing_registrations = [
            registration
            for registration in self.registrations
            if registration.user_id == user.id and registration.status in statuses
        ]
        return any(existing_registrations)

    def is_rejected(self, user):
        return self.is_registered_with_status(user, [RegistrationStatus.Rejected])

    def can_self_register(self, user, time):
        if not self.is_confirmed():
            return False
        if self.is_leader(user) or self.is_registered(user):
            return False
        return self.has_free_online_slots() and self.is_registration_open_at_time(time)

    # Status
    def is_confirmed(self):
        return self.status == EventStatus.Confirmed

    def status_string(self):
        return EventStatus(self.status).display_name()
