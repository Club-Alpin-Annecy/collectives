# This file describe all classes we will use in collectives
from .helpers import current_time

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy_utils import PasswordType, force_auto_coercion
from flask_uploads import UploadSet, IMAGES
from delta import html
from wtforms.validators import Email, Length

from datetime import datetime, date
import json
import enum

# Create database connection object
db = SQLAlchemy()
force_auto_coercion()

# Upload
photos = UploadSet('photos', IMAGES)
avatars = UploadSet('avatars', IMAGES)

# Utility enums


class RoleIds(enum.IntEnum):
    # Global roles
    Moderator = 1
    Administrator = 2
    President = 3
    # Activity-related roles
    EventLeader = 10
    ActivitySupervisor = 11

    @classmethod
    def display_names(cls):
        return {
            cls.Administrator: 'Administrateur',
            cls.Moderator: 'Modérateur',
            cls.President: 'Président du club',
            cls.EventLeader: 'Initiateur',
            cls.ActivitySupervisor: "Responsable d'activité"
        }

    def display_name(self):
        cls = self.__class__
        return cls.display_names()[self.value]

    def relates_to_activity(self):
        cls = self.__class__
        return self.value in [cls.ActivitySupervisor, cls.EventLeader]


class RegistrationLevels(enum.IntEnum):
    Normal = 0
    CoLeader = 1


class RegistrationStatus(enum.IntEnum):
    Active = 0
    Rejected = 1

# Utility tables


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

# Models


class User(db.Model, UserMixin):
    """ Utilisateurs """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    # E-mail
    mail = db.Column(db.String(100),
                     nullable=False,
                     unique=True,
                     index=True,
                     info={'validators': Email(message="E-mail invalide"),
                           'label': 'Email'})

    # Name
    first_name = db.Column(db.String(100),
                           nullable=False,
                           info={'label': 'Prénom'})
    last_name = db.Column(db.String(100),
                          nullable=False,
                          info={'label': 'Nom'})

    # License number
    license = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
        info={'label': 'Numéro de licence',
              'validators': Length(
                  min=12, max=12,
                  message="Numéro de licence invalide")})

    # Date of birth
    date_of_birth = db.Column(
        db.Date, nullable=False, default=date.today(), 
        info={'label': 'Date de naissance'})

    # Hashed password
    password = db.Column(PasswordType(schemes=['pbkdf2_sha512']),
                         nullable=True,
                         info={'label': 'Mot de passe'})

    # Custom avatar
    avatar = db.Column(db.String(100), nullable=True)

    # Contact info
    phone = db.Column(db.String(20), info={'label': 'Téléphone'})
    emergency_contact_name = db.Column(
        db.String(100), nullable=False, default='',
        info={'label': 'Personne à contacter en cas d\'urgence'})
    emergency_contact_phone = db.Column(
        db.String(20), nullable=False, default='',
        info={'label': 'Téléphone en cas d\'urgence'})

    # Internal
    enabled = db.Column(db.Boolean,
                        default=True,
                        info={'label': 'Utilisateur activé'})

    license_expiry_date = db.Column(db.Date)
    last_extranet_sync_time = db.Column(db.DateTime)

    # List of protected field, which cannot be modified by a User
    protected = ['enabled', 'license', 'date_of_birth', 'license_expiry_date',
                 'last_extranet_sync_time']

    # Relationships
    roles = db.relationship('Role', backref='user', lazy=True)
    registrations = db.relationship('Registration', backref='user', lazy=True)

    def save_avatar(self, file):
        if file is not None:
            filename = avatars.save(file, name='user-' + str(self.id) + '.')
            self.avatar = filename

    def check_license_valid_at_time(self, time):
        if self.license_expiry_date is None:
            # Test users licenses never expire
            return True
        return self.license_expiry_date > time.date()

    def matching_roles(self, role_ids):
        return [role for role in self.roles if role.role_id in role_ids]

    def matching_roles_for_activity(self, role_ids, activity_id):
        matching_roles = self.matching_roles(role_ids)
        return [role for role in matching_roles if role.activity_id == activity_id]

    def has_role(self, role_ids):
        return len(self.matching_roles(role_ids)) > 0

    def has_role_for_activity(self, role_ids, activity_id):
        roles = self.matching_roles(role_ids)
        return any([role.activity_id == activity_id for role in roles])

    def is_admin(self):
        return self.has_role([RoleIds.Administrator])

    def is_moderator(self):
        return self.has_role([RoleIds.Moderator,
                              RoleIds.Administrator,
                              RoleIds.President])

    def can_create_events(self):
        return self.has_role([RoleIds.EventLeader,
                              RoleIds.ActivitySupervisor,
                              RoleIds.President,
                              RoleIds.Administrator])

    def can_lead_activity(self, activity_id):
        return self.has_role_for_activity([RoleIds.EventLeader,
                                           RoleIds.ActivitySupervisor],
                                          activity_id)

    def can_read_other_users(self):
        return len(self.roles) > 0

    def supervises_activity(self, activity_id):
        return self.has_role_for_activity([RoleIds.ActivitySupervisor],
                                          activity_id)

    def led_activities(self):
        roles = self.matching_roles([RoleIds.EventLeader,
                                     RoleIds.ActivitySupervisor])
        return set([role.activity_type for role in roles])

    # Format

    def full_name(self):
        return '{} {}'.format(self.first_name, self.last_name.upper())

    def abbrev_name(self):
        return '{} {}'.format(self.first_name, self.last_name[0].upper())

    @property
    def is_active(self):
        return self.enabled and self.check_license_valid_at_time(current_time())


class ActivityType(db.Model):
    """ Activités """

    __tablename__ = 'activity_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    short = db.Column(db.String(256), nullable=False)

    # Relationships
    persons = db.relationship('Role', backref='activity_type', lazy=True)

    def can_be_led_by(self, users):
        for user in users:
            if user.can_lead_activity(self.id):
                return True
        return False


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
        if self.is_leader(user) or self.is_registered(user):
            return False
        return self.has_free_online_slots() and self.is_registration_open_at_time(time)


class Role(db.Model):
    """ Roles utilisateurs: Administrateur, Modérateur, Encadrant/Reponsable
        activité... """

    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    activity_id = db.Column(db.Integer,
                            db.ForeignKey('activity_types.id'),
                            nullable=True)
    role_id = db.Column(db.Integer, nullable=False)

    def name(self):
        return RoleIds(self.role_id).display_name()


class Registration(db.Model):
    """ Participants à la collective (adhérents lambda, dont co-encadrants) """
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), index=True)
    status = db.Column(db.Integer, nullable=False)  # Active, Rejected...
    level = db.Column(db.Integer, nullable=False)  # Co-encadrant, Normal

    def is_active(self):
        return self.status == RegistrationStatus.Active

    def is_rejected(self):
        return self.status == RegistrationStatus.Rejected
