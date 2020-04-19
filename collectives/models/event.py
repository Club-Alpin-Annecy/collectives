"""Module for event related classes
"""
from flask_uploads import UploadSet, IMAGES

from .globals import db
from .registration import RegistrationStatus
from .utils import ChoiceEnum
from .activitytype import activities_without_leader

from ..utils import render_markdown

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

    main_leader_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    """ Primary key of the registered user (see  :py:class:`collectives.models.user.User`)

    :type: int"""

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

        :param file: The direct output of a FileInput
        :type file: :py:class:`werkzeug.datastructures.FileStorage`
        """
        if file is not None:
            filename = photos.save(file, name="event-" + str(self.id) + ".")
            self.photo = filename

    def set_rendered_description(self, description):
        """Render description and returns it.

        :param description: Markdown description.
        :type description: string
        :return: Rendered :py:attr:`description` as HTML
        :rtype: string
        """
        self.rendered_description = render_markdown.markdown_to_html(description)
        return self.rendered_description

    # Date validation
    def has_defined_registration_date(self):
        """ Check if this event has online registration date

        An event should not be created with online slot defined but without
        registration dates (open and close).

        :return: Is both :py:attr:`registration_open_time` and
             :py:attr:`registration_close_time` are defined?
        :rtype: boolean
        """
        if not self.registration_open_time or not self.registration_close_time:
            return False
        return True

    def starts_before_ends(self):
        """ Check if this event has right date order.

        An event end should be after the start.

        :return: Is :py:attr:`start` anterior to :py:attr:`end` ?
        :rtype: boolean
        """
        return self.start <= self.end

    def opens_before_closes(self):
        """ Check if this event has right registration date order.

        An event registration end should be after the registration start.

        :return: Is :py:attr:`registration_open_time` anterior to
             :py:attr:`registration_close_time` ?
        :rtype: boolean
        """
        return self.registration_open_time <= self.registration_close_time

    def opens_before_ends(self):
        """ Check if this event opens registration before its end.

        An event end should be after the registration start.

        :return: Is :py:attr:`registration_open_time` anterior to
             :py:attr:`end` ?
        :rtype: boolean
        """
        return self.registration_open_time <= self.end

    def closes_before_starts(self):
        """ Check if this event closes registrations before starting.
        This should be the case for "normal" events, see #159

        :return: Is :py:attr:`registration_close_time` anterior to
             :py:attr:`start` ?
        :rtype: boolean
        """
        return self.registration_close_time <= self.start

    def has_valid_slots(self):
        """ Check if this event does not have more online slots than overall
        slots.

        :return: True if event has a good configuration of num_slots.
        :rtype: boolean
        """
        # pylint: disable=C0301
        return self.num_online_slots >= 0 and self.num_slots >= self.num_online_slots

    def has_valid_leaders(self):
        """
        :return: True if current leaders can lead all activities. If activities are empty, returns False.
        :seealso: :py:meth:`activities_without_leader`
        """
        if not any(self.activity_types):
            return False
        return not any(activities_without_leader(self.activity_types, self.leaders))

    def ranked_leaders(self):
        """
        :return: the list of leaders in which the main one comes first
        :rtype: list(:py:class:`collectives.models.user.User`)
        """
        main_leader = None
        other_leaders = []
        for l in self.leaders:
            if l.id == self.main_leader_id:
                main_leader = l
            else:
                other_leaders.append(l)
        if main_leader is None:
            return other_leaders
        return [main_leader] + other_leaders

    def is_valid(self):
        """Check if current event is valid.

        This method performs various operation to check integrity of event
        such as date order, or leader rights. See:
        * :py:meth:`starts_before_ends`
        * :py:meth:`has_valid_slots`
        * :py:meth:`has_valid_leaders`
        * :py:meth:`opens_before_closes`
        * :py:meth:`has_defined_registration_date`

        :return: True if all tests are succesful
        :rtype: boolean
        """
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
        """Check if a user is one of this event leaders.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user is a leader.
        :rtype: boolean """
        return user in self.leaders

    def is_supervisor(self, user):
        """Check if a user is a supervisor of one of the event activities.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user supervises one of the event activities.
        :rtype: boolean
        """
        return any([a for a in self.activity_types if user.supervises_activity(a.id)])

    def has_edit_rights(self, user):
        """ Check if a user can edit this event.

        Returns true if either:
         - event is WIP (not created yet)
         - user is leader of this event
         - user supervises any of this event activities
         - user is moderator

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user can edit the event.
        :rtype: boolean
        """
        if self.id is None:
            return True

        if user.is_moderator():
            return True
        return self.is_leader(user) or self.is_supervisor(user)

    def has_delete_rights(self, user):
        """ Check if a user can delete this event.

        Returns true if either:
         - user supervises any of this event activities
         - user is moderator

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user can delete the event.
        :rtype: boolean
        """
        return user.is_moderator() or self.is_supervisor(user)

    def can_remove_leader(self, user, leader):
        """
        Returns true if either:
         - user supervises any of this event activities
         - user is moderator
         - user is leader of this event and is not removing themselves
        """
        if not self.has_edit_rights(user):
            return False
        if user != leader:
            return True

        return user.is_moderator() or self.is_supervisor(user)

    # Registrations
    def is_registration_open_at_time(self, time):
        """ Check if online registration for this event is open.

        :param time: Time that will be checked (usually, current time).
        :type time: :py:class:`datetime.datetime`
        :return: True if registration is open at ``time``
        :rtype: boolean
        """
        # pylint: disable=C0301
        return self.registration_open_time <= time <= self.registration_close_time

    def active_registrations(self):
        """ Returns all actives registrations.

        See :py:meth:`collectives.models.registration.Registration.is_active`

        :return: All registration of this event which are active
        :rtype: list(:py:class:`collectives.models.registration.Registration`)
        """
        # pylint: disable=C0301
        return [
            registration
            for registration in self.registrations
            if registration.is_active()
        ]

    def has_free_slots(self):
        """ Check if this event is full.

        :return: True if there is less active registrations than available slots.
        :rtype: boolean
        """
        return len(self.active_registrations()) < self.num_slots

    def has_free_online_slots(self):
        """ Check if an user can self-register.

        :return: True if there is less active registrations than available
                online slots.
        :rtype: boolean
        """
        return len(self.active_registrations()) < self.num_online_slots

    def free_slots(self):
        """ Calculate the amount of available slot for new registrations.

        :return: Number of free slots for this event.
        :rtype: int """
        free = self.num_slots - len(self.active_registrations())
        return 0 if free < 0 else free

    def is_registered(self, user):
        """ Check if a user is registered to this event.

        Note:
        - leader is not considered as registered.
        - a rejected user user is still considered as registered.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user is registered.
        :rtype: boolean
        """
        existing_registrations = [
            registration
            for registration in self.registrations
            if registration.user_id == user.id
        ]
        return any(existing_registrations)

    def is_registered_with_status(self, user, statuses):
        """ Check if a user is registered to this event with specific status.

        Note:
        - leader is not considered as registered.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :param statuses: Status acceptable to test registrations.
        :type statuses: list(:py:class:`collectives.models.registration.RegistrationStatus`)
        :return: True if user is registered with a specific status
        :rtype: boolean
        """
        existing_registrations = [
            registration
            for registration in self.registrations
            if registration.user_id == user.id and registration.status in statuses
        ]
        return any(existing_registrations)

    def is_rejected(self, user):
        """ Check if a user is rejected on this event.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user is registered with a ``rejected`` status
        :rtype: boolean
        """
        return self.is_registered_with_status(user, [RegistrationStatus.Rejected])

    def can_self_register(self, user, time):
        """ Check if a user can self-register.

        An user can self-register if:
          - he has no current registration with this event.
          - he is not a leader of this event.
          - given time parameter (usually current_time) is in registration
            time.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :param time: Time that will be checked (usually, current time).
        :type time: :py:class:`datetime.datetime`
        :return: True if user can self-register.
        :rtype: boolean
        """
        if not self.is_confirmed():
            return False
        if self.is_leader(user) or self.is_registered(user):
            return False
        return self.has_free_online_slots() and self.is_registration_open_at_time(time)

    # Status
    def is_confirmed(self):
        """ Check if this event is confirmed.

        See: :py:class:`EventStatus`

        :return: True if this event has ``Confirmed`` status.
        :rtype: boolean """
        return self.status == EventStatus.Confirmed

    def status_string(self):
        """ Get the event status as a string to display.

        See: :py:meth:`EventStatus.display_name`

        :return: The status of the event.
        :rtype: string """
        return EventStatus(self.status).display_name()
