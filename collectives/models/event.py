# This file describe all classes we will use in collectives

from flask import current_app
from flask_uploads import UploadSet, IMAGES
import markdown
import re

from . import db
from .registration import RegistrationStatus
from .utils import ChoiceEnum

photos = UploadSet('photos', IMAGES)


class EventStatus(ChoiceEnum):
    Confirmed = 0
    Pending = 1
    Cancelled = 2

    @classmethod
    def display_names(cls):
        return {
            cls.Confirmed: 'Confirmée',
            cls.Pending: 'En attente',
            cls.Cancelled: 'Annulée'
        }



# Reponsables d'une collective (avec droits de modifs sur ladite collective,
#  pas comptés dans le nombre de place
event_leaders = db.Table('event_leaders',
                         db.Column(
                             'user_id',
                             db.Integer,
                             db.ForeignKey('users.id'),
                             index=True),
                         db.Column(
                             'event_id',
                             db.Integer,
                             db.ForeignKey('events.id'),
                             index=True)
                         )

# Objets (activités) de la collective. Contrainte: Pour chaque activite de la
# collective il doit exister un co-responsable cable de l'encadrer
event_activity_types = db.Table('event_activity_types',
                                db.Column('activity_id',
                                          db.Integer,
                                          db.ForeignKey('activity_types.id'),
                                          index=True),
                                db.Column(
                                    'event_id',
                                    db.Integer,
                                    db.ForeignKey('events.id'),
                                    index=True)
                                )


class Event(db.Model):
    """ Collectives """

    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text(), nullable=False, default='')
    rendered_description = db.Column(db.Text(), nullable=True, default='')
    photo = db.Column(db.String(100), nullable=True)
    start = db.Column(db.DateTime, nullable=False, index=True)
    end = db.Column(db.DateTime, nullable=False)

    num_slots = db.Column(db.Integer, nullable=False)
    num_online_slots = db.Column(db.Integer, nullable=False)
    registration_open_time = db.Column(db.DateTime, nullable=True)
    registration_close_time = db.Column(db.DateTime, nullable=True)

    status = db.Column(db.Enum(EventStatus), nullable=False,
                       default=EventStatus.Confirmed,
                       info={'choices': EventStatus.choices(),
                             'coerce': EventStatus.coerce})

    # Relationships
    leaders = db.relationship('User',
                              secondary=event_leaders,
                              lazy='subquery',
                              backref=db.backref(
                                  'led_events',
                                  lazy=True,
                                  order_by='Event.start'))
    activity_types = db.relationship('ActivityType',
                                     secondary=event_activity_types,
                                     lazy='subquery',
                                     backref=db.backref(
                                         'events', lazy=True))
    registrations = db.relationship('Registration', backref='event', lazy=True,
                                    cascade="all, delete-orphan")

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.description = current_app.config['DESCRIPTION_TEMPLATE']
        # Remove placeholders
        self.description = re.sub(r'\$[\w]+?\$', '', self.description)

    def save_photo(self, file):
        if file is not None:
            filename = photos.save(file, name='event-' + str(self.id) + '.')
            self.photo = filename

    def set_rendered_description(self, description):
        # Urify links
        # From https://daringfireball.net/2010/07/improved_regex_for_matching_urls
        URI_REGEX = r'(?i)(^|^\s|[^(]\s+|[^\]]\(\s*)((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))'
        description = re.sub(URI_REGEX, r'\1[\2](\2)', description)
        self.rendered_description = markdown.markdown(description, extensions=['nl2br'])
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
            return (self.starts_before_ends() and
                    self.has_valid_slots() and
                    self.has_valid_leaders())
        else:
            return (self.starts_before_ends() and
                    self.has_valid_slots() and
                    self.has_valid_leaders() and
                    self.starts_before_ends() and
                    self.opens_before_closes() and
                    self.has_defined_registration_date())

    def is_leader(self, user):
        return user in self.leaders

    def is_supervisor(self, user):
        return any(
            [a for a in self.activity_types if user.supervises_activity(a.id)])

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
        # pylint: disable=C0301
        return time >= self.registration_open_time and time <= self.registration_close_time

    def active_registrations(self):
        # pylint: disable=C0301
        return [
            registration for registration in self.registrations if registration.is_active()]

    def has_free_slots(self):
        return len(self.active_registrations()) < self.num_slots

    def has_free_online_slots(self):
        return len(self.active_registrations()) < self.num_online_slots

    def free_slots(self):
        free = self.num_slots - len(self.active_registrations())
        return 0 if free < 0 else free

    def is_registered(self, user):
        # pylint: disable=C0301
        existing_registrations = [
            registration for registration in self.registrations if registration.user_id == user.id]
        return any(existing_registrations)

    def is_registered_with_status(self, user, statuses):
        # pylint: disable=C0301
        existing_registrations = [
            registration for registration in self.registrations if registration.user_id == user.id and registration.status in statuses]
        return any(existing_registrations)

    def is_rejected(self, user):
        return self.is_registered_with_status(
            user, [RegistrationStatus.Rejected])

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
