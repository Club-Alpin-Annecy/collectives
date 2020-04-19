"""Module for user related classes

"""
import os
from datetime import date, datetime

from flask_login import UserMixin
from sqlalchemy_utils import PasswordType
from flask_uploads import UploadSet, IMAGES
from wtforms.validators import Email

from .globals import db
from .role import RoleIds, Role
from .activitytype import ActivityType
from .utils import ChoiceEnum
from ..helpers import current_time

# Upload
avatars = UploadSet("avatars", IMAGES)


class Gender(ChoiceEnum):
    """Enum to store User gender
    """

    Unknown = 0
    """Default gender if not known """
    Woman = 1
    """Woman gender """
    Man = 2
    """Man gender"""
    Other = 3
    """Other gender"""

    @classmethod
    def display_names(cls):
        """ Return all available gender with their names.

        :return: The list of gender in a dictionnary that link its id with
            the display names.
        :rtype: dictionnary
        """
        return {
            cls.Other: "Autre",
            cls.Woman: "Femme",
            cls.Man: "Homme",
            cls.Unknown: "Inconnu",
        }


# Models
class User(db.Model, UserMixin):
    """ Class to manage user.

    Persistence is managed by SQLAlchemy. This class is used by ``flask_login``
    to manage acccess to the system.
    """

    __tablename__ = "users"
    """Name of the table for persistence by sqlalchemy"""

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key.

    :type: int
    """

    is_test = db.Column(
        db.Boolean, default=True, nullable=False, info={"label": "Utilisateur de test"}
    )
    """Attribute to know if the user is real or just for tests

    :type: boolean
    """

    # E-mail
    mail = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
        info={
            "validators": Email(message="Format d'adresse invalide"),
            "label": "Adresse e-mail",
        },
    )
    """ User email address.

    :type: string """

    first_name = db.Column(db.String(100), nullable=False, info={"label": "Prénom"})
    """ User first name.

    :type: string """
    last_name = db.Column(db.String(100), nullable=False, info={"label": "Nom"})
    """ User last name.

    :type: string """

    license = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
        info={"label": "Numéro de licence"},
    )
    """ User club license number.

    :type: string (100 char)'"""

    license_category = db.Column(db.String(2), info={"label": "Catégorie de licence"})
    """ User club license category.

    :type: string (2 char)"""

    # Date of birth
    date_of_birth = db.Column(
        db.Date,
        nullable=False,
        default=date.today(),
        info={"label": "Date de naissance"},
    )
    """ User date of birth.

    :type: :py:class:`datetime.date`"""

    password = db.Column(
        PasswordType(schemes=["pbkdf2_sha512"]),
        nullable=True,
        info={"label": "Mot de passe"},
    )
    """ Hashed password.

    Hash is done with pbkdf2_sha512: https://fr.wikipedia.org/wiki/PBKDF2 .

    :type: string """

    avatar = db.Column(db.String(100), nullable=True)
    """ URL to avatar file.

    :type: string"""

    # Contact info
    phone = db.Column(db.String(20), info={"label": "Téléphone"})
    """ User phone number.

    :type: string (20 char)
    """
    emergency_contact_name = db.Column(
        db.String(100),
        nullable=False,
        default="",
        info={"label": "Personne à contacter en cas d'urgence"},
    )
    """ Name of User emergency contact.

    :type: string (100 char)
    """
    emergency_contact_phone = db.Column(
        db.String(20),
        nullable=False,
        default="",
        info={"label": "Téléphone en cas d'urgence"},
    )
    """ Phone number of User emergency contact.

    :type: string (20 char)
    """

    # Internal
    enabled = db.Column(db.Boolean, default=True, info={"label": "Utilisateur activé"})
    """ User status.

    Only an enabled user can login.

    :type: boolean
    """

    license_expiry_date = db.Column(db.Date)
    """ User license expiration date.

    :type: :py:class:`datetime.date`"""

    last_extranet_sync_time = db.Column(db.DateTime)
    """ Last synchronisation date of user profile with FFCAM extranet.

    :type: :py:class:`datetime.datetime`"""

    gender = db.Column(
        db.Enum(Gender),
        nullable=False,
        default=Gender.Unknown,
        info={"label": "Genre", "choices": Gender.choices(), "coerce": Gender.coerce},
    )
    """ User gender.

    For a user from FFCAM extranet, it is guessed from its title. See
    :py:func:`collectives.utils.extranet.sync_user`.

    :type: :py:class:`Gender`"""

    last_failed_login = db.Column(
        db.DateTime, nullable=False, default=datetime(2000, 1, 1)
    )
    """ Last failed login attempt on user account.

    It is the date of the last time a wrong password has been used to connect.
    It is used to rate limit login attempt. See
    :py:func:`collectives.routes.auth.login`.

    :type: :py:class:`datetime.datetime`"""

    confidentiality_agreement_signature_date = db.Column(
        db.DateTime,
        nullable=True,
        info={"label": "Date de signature de la charte RGPD"},
    )
    """ Date of the signature of confidentiality agreement.

    The agreement signature is mandatory for all users with special functions
    within this site. If it has not been signed,
    `confidentiality_agreement_signature_date` is null.

    :type: :py:class:`datetime.datetime`"""

    legal_text_signature_date = db.Column(
        db.DateTime,
        nullable=True,
        info={"label": "Date de signature des mentions légales"},
    )
    """ Date of the signature of the legal terms.

    All user must sign the legal term at account creation. If it has not been
    signed (usually test account), `confidentiality_agreement_signature_date`
    is null.

    :type: :py:class:`datetime.datetime`"""

    # Relationships
    roles = db.relationship("Role", backref="user", lazy=True)
    """ List of granted roles within this site for this user. (eg administrator)

    :type: list(:py:class:`collectives.models.role.Role`)"""

    registrations = db.relationship("Registration", backref="user", lazy=True)
    """ List registration of the user.

    :type: list(:py:class:`collectives.models.registration.Registration`)
    """

    def save_avatar(self, file):
        if file is not None:
            filename = avatars.save(file, name="user-" + str(self.id) + ".")
            self.avatar = filename

    def delete_avatar(self):
        if self.avatar:
            os.remove(avatars.path(self.avatar))
            self.avatar = None

    def get_gender_name(self):
        return Gender(self.gender).display_name()

    def check_license_valid_at_time(self, time):
        if self.is_test:
            # Test users licenses never expire
            return True
        return self.license_expiry_date > time.date()

    def is_youth(self):
        return self.license_category in ["J1", "E1"]

    def is_minor(self):
        return self.license_category in ["J2", "E2"]

    # Roles

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
        return self.has_role(RoleIds.all_moderator_roles())

    def is_supervisor(self):
        return self.has_role([RoleIds.ActivitySupervisor])

    def can_create_events(self):
        return self.has_role(RoleIds.all_event_creator_roles())

    def can_lead_activity(self, activity_id):
        return self.has_role_for_activity(
            RoleIds.all_activity_leader_roles(), activity_id
        )

    def can_lead_activities(self, activities):
        return all(self.can_lead_activity(a.id) for a in activities)

    def can_read_other_users(self):
        return self.has_signed_ca() and self.has_any_role()

    def has_any_role(self):
        return len(self.roles) > 0

    def has_signed_ca(self):
        return self.confidentiality_agreement_signature_date is not None

    def has_signed_legal_text(self):
        return self.legal_text_signature_date is not None

    def supervises_activity(self, activity_id):
        return self.has_role_for_activity([RoleIds.ActivitySupervisor], activity_id)

    def led_activities(self):
        roles = self.matching_roles(RoleIds.all_activity_leader_roles())
        return set(role.activity_type for role in roles)

    # Format

    def full_name(self):
        return "{} {}".format(self.first_name, self.last_name.upper())

    def abbrev_name(self):
        return "{} {}".format(self.first_name, self.last_name[0].upper())

    def get_supervised_activities(self):
        if self.is_admin():
            return ActivityType.query.all()

        roles = self.matching_roles([RoleIds.ActivitySupervisor])
        return [role.activity_type for role in roles]

    @property
    def is_active(self):
        return self.enabled and self.check_license_valid_at_time(current_time())


def activity_supervisors(activities):
    """
    Returns all supervisors for a list of activities

    :return: List of all activities for configuration
    :rtype: Array
    """
    activity_ids = [a.id for a in activities]
    query = db.session.query(User)
    query = query.filter(Role.activity_id.in_(activity_ids))
    query = query.filter(Role.role_id == RoleIds.ActivitySupervisor)
    query = query.filter(User.id == Role.user_id)
    return query.all()
