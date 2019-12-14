# This file describe all classes we will use in collectives

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy_utils import PasswordType, force_auto_coercion
from datetime import datetime
from flask_uploads import UploadSet, IMAGES
from delta import html
import json
import enum

# Create database connection object
db = SQLAlchemy()
force_auto_coercion()

# Upload
photos  = UploadSet('photos', IMAGES)
avatars = UploadSet('avatars', IMAGES)

# Utility enums

class RoleIds(enum.IntEnum):
    # Global roles
    Moderator =  1
    Administrator = 2
    President = 3
    # Activity-related roles
    EventLeader = 10
    ActivitySupervisor = 11

    @classmethod
    def display_names(cls):
        return {
            cls.Administrator : "Administrateur",
            cls.Moderator : "Modérateur",
            cls.President : "Président du club",
            cls.EventLeader : "Initiateur",
            cls.ActivitySupervisor : "Responsable d'activité"
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
    Active = 0,
    Rejected = 1

# Utility tables

""" Reponsables d'une collective (avec droits de modifs sur ladite collective,
    pas comptés dans le nombre de place """
event_leaders = db.Table('event_leaders',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), index=True),
    db.Column('event_id', db.Integer, db.ForeignKey('events.id'), index=True)
)

""" Objets (activités) de la collective. Contrainte: Pour chaque activite de la
        collective il doit exister un co-responsable cable de l'encadrer"""
event_activity_types = db.Table('event_activity_types',
    db.Column('activity_id', db.Integer, db.ForeignKey('activity_types.id'), index=True),
    db.Column('event_id', db.Integer, db.ForeignKey('events.id'), index=True)
    )

# Models

class User(db.Model, UserMixin):
    """ Utilisateurs """

    __tablename__ = 'users'

    id              = db.Column(db.Integer, primary_key=True)
    mail            = db.Column(db.String(100), nullable=False, info={'label': 'Email'} )
    first_name      = db.Column(db.String(100), nullable=False, info={'label': 'Prénom'})
    last_name       = db.Column(db.String(100), nullable=False, info={'label': 'Nom'})
    license         = db.Column(db.String(100),                 info={'label': 'Numéro de licence'})
    phone           = db.Column(db.String(20),                  info={'label': 'Téléphone'})
    password        = db.Column(PasswordType(schemes=['pbkdf2_sha512']), info={'label': 'Mot de passe'}, nullable=True )
    avatar          = db.Column(db.String(100), nullable=True)

    enabled         = db.Column(db.Boolean, default=True,       info={'label': 'Utilisateur activé'})

    # List of protected field, which cannot be modified by a User
    protected       = ['enabled']

    #Relationships
    roles = db.relationship('Role', backref='user', lazy=True)
    registrations = db.relationship('Registration', backref='user', lazy=True)

    def save_avatar(self, file):
        if file != None:
            filename = avatars.save(file, name='user-'+str(self.id)+'.')
            self.avatar = filename;

    def check_license_valid_at_time(self, time):
        # TODO:
        return True

    def has_role(self, role_ids):
        return any([role.role_id in role_ids for role in self.roles])

    def has_role_for_activity(self, role_ids, activity_id):
        return any([role.role_id in role_ids and role.activity_id  == activity_id for role in self.roles])

    def is_admin(self):
        return self.has_role([RoleIds.Administrator])

    def is_moderator(self):
        return self.has_role([RoleIds.Moderator, RoleIds.Administrator, RoleIds.President]) 
    
    def can_create_events(self):
        return self.has_role([RoleIds.EventLeader, RoleIds.ActivitySupervisor, RoleIds.President, RoleIds.Administrator]) 

    def can_lead_activity(self, activity_id):
        return self.has_role_for_activity([RoleIds.EventLeader, RoleIds.ActivitySupervisor], activity_id)

    def supervises_activity(self, activity_id):
        return self.has_role_for_activity([RoleIds.ActivitySupervisor], activity_id)

    # Format

    def full_name(self):
        return '{} {}'.format(self.first_name, self.last_name.upper())

    def abbrev_name(self):
        return '{} {}'.format(self.first_name, self.last_name[0].upper())

    def is_active(self):
        return self.enabled

class ActivityType(db.Model):
    """ Activités """

    __tablename__ = 'activity_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable = False)
    short = db.Column(db.String(256), nullable = False)
    
    #Relationships
    persons = db.relationship('Role', backref='activity_type', lazy=True)

class Event(db.Model):
    """ Collectives """

    __tablename__ = 'events'

    id              = db.Column(db.Integer, primary_key=True)
    title           = db.Column(db.String(100), nullable=False)
    description     = db.Column(db.Text(), nullable=False, default="")
    rendered_description =  db.Column(db.Text(), nullable=True, default="")
    shortdescription= db.Column(db.String(100), nullable=True, default="")
    photo           = db.Column(db.String(100), nullable=True)
    start           = db.Column(db.DateTime, nullable=False, index=True)
    end             = db.Column(db.DateTime, nullable=False)

    num_slots = db.Column(db.Integer, nullable = False)
    num_online_slots = db.Column(db.Integer, nullable = False)
    registration_open_time = db.Column(db.DateTime, nullable=False)
    registration_close_time = db.Column(db.DateTime, nullable=False)

    # Relationships
    leaders = db.relationship('User', secondary=event_leaders, lazy='subquery',
        backref=db.backref('led_events', lazy=True, order_by='Event.start'))
    activity_types = db.relationship('ActivityType', secondary=event_activity_types, lazy='subquery',
        backref=db.backref('events', lazy=True))
    registrations = db.relationship('Registration', backref='event', lazy=True)

    def save_photo(self, file):
        if file != None:
            filename = photos.save(file, name='event-'+str(self.id)+'.')
            self.photo = filename;

    def set_rendered_description(self, description):
        self.rendered_description=html.render(json.loads(description)['ops'])
        return self.rendered_description

    # Date validation

    def starts_before_ends(self):
        # Event must starts before it ends
        return self.start.date() <= self.end

    def opens_before_closes(self):
        # Registrations must open before they close
        return self.registration_open_time <= self.registration_close_time

    def opens_before_ends(self):
        # Registrations must open before event ends
        return self.registration_open_time.date() <= self.end

    def has_valid_slots(self):
        return self.num_online_slots >= 0 and self.num_slots >= self.num_online_slots

    def has_valid_leaders(self):
        if not any(self.activity_types):
            return False
        return not any([not any([user.can_lead_activity(activity.id) for user in self.leaders]) for activity in self.activity_types])

    def is_valid(self):
        return self.starts_before_ends() and self.opens_before_closes() and self.opens_before_ends()  and  self.has_valid_slots() and self.has_valid_leaders()

    def is_leader(self, user):
        return user in self.leaders

    def has_edit_rights(self, user):
        return self.is_leader(user) or user.is_admin() or any(
            [activity for activity in self.activity_types if user.supervises_activity(activity.id)])

    # Registrations

    def is_registration_open_at_time(self, time):
        return time >= self.registration_open_time and time <= self.registration_close_time

    def active_registrations(self):
        return [registration for registration in self.registrations if registration.is_active()]

    def has_free_slots(self):
        return len(self.active_registrations()) < self.num_online_slots

    def is_registered(self, user):
        existing_registrations = [registration for registration in self.registrations if registration.user_id == user.id]
        return any(existing_registrations)

    def is_registered_with_status(self, user, statuses):
        existing_registrations = [registration for registration in self.registrations if registration.user_id == user.id and registration.status in statuses ]
        return any(existing_registrations)
    
    def is_rejected(self, user):
        return self.is_registered_with_status(user, [RegistrationStatus.Rejected])

    def can_self_register(self, user, time):
        if self.is_leader(user) or self.is_registered(user):
            return False
        return self.has_free_slots() and self.is_registration_open_at_time(time)

class Role(db.Model):
    """ Roles utilisateurs: Administrateur, Modérateur, Encadrant/Reponsable activité... """

    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activity_types.id"), nullable=True)
    role_id = db.Column(db.Integer, nullable = False)

    def name(self):
        return RoleIds(self.role_id).display_name()

class Registration(db.Model):
    """ Participants à la collective (adhérents lambda, dont co-encadrants) """
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), index=True)
    status = db.Column(db.Integer, nullable = False) # Active, Rejected...
    level = db.Column(db.Integer, nullable = False)  # Co-encadrant, Normal

    def is_active(self):
        return self.status == RegistrationStatus.Active
    
    def is_rejected(self):
        return self.status == RegistrationStatus.Rejected
