# This file describe all classes we will use in collectives

from flask import current_app
from flask_uploads import UploadSet, IMAGES
from delta import html
import json
import enum
import re

from . import db
from .registration import RegistrationStatus

photos = UploadSet('photos', IMAGES)


class EventStatus(enum.IntEnum):
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

    def display_name(self):
        cls = self.__class__
        return cls.display_names()[self.value]


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
    shortdescription = db.Column(db.String(100), nullable=True, default='')
    photo = db.Column(db.String(100), nullable=True)
    start = db.Column(db.DateTime, nullable=False, index=True)
    end = db.Column(db.DateTime, nullable=False)

    num_slots = db.Column(db.Integer, nullable=False)
    num_online_slots = db.Column(db.Integer, nullable=False)
    registration_open_time = db.Column(db.DateTime, nullable=False)
    registration_close_time = db.Column(db.DateTime, nullable=False)

    status = db.Column(db.Integer, nullable=False,
                       default=EventStatus.Confirmed)

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
    registrations = db.relationship('Registration', backref='event', lazy=True)

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
        self.rendered_description = html.render(json.loads(description)['ops'])
        return self.rendered_description

    # Date validation

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
        # pylint: disable=C0301
        return self.starts_before_ends() and self.opens_before_closes(
        ) and self.opens_before_ends() and self.has_valid_slots() and self.has_valid_leaders()

    def is_leader(self, user):
        return user in self.leaders

    def has_edit_rights(self, user):
        # pylint: disable=C0301
        return self.is_leader(user) or user.is_admin() or any(
            [activity for activity in self.activity_types if user.supervises_activity(activity.id)])

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
        return self.num_slots - len(self.active_registrations())

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

    def status_string (self):
        return EventStatus(self.status).display_name()
