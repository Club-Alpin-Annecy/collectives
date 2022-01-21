"""Module for user related classes

"""
import os
from datetime import date, datetime

from flask_login import UserMixin
from flask import current_app
from sqlalchemy_utils import PasswordType
from sqlalchemy.orm import validates
from flask_uploads import UploadSet, IMAGES
from wtforms.validators import Email

from .globals import db
from .role import RoleIds, Role
from .activitytype import ActivityType
from .utils import ChoiceEnum
from ..utils.time import current_time

# Upload
avatars = UploadSet("avatars", IMAGES)


class Gender(ChoiceEnum):
    """Enum to store User gender"""

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
        """Return all available gender with their names.

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
    """Class to manage user.

    Persistence is managed by SQLAlchemy. This class is used by ``flask_login``
    to manage acccess to the system.

    Test users are special users created directly by admin. They have their licence
    validity always true and their personnal information can be modified by
    administrators. The parameter is :py:attr:`is_test`
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

    legal_text_signed_version = db.Column(
        db.Integer,
        nullable=True,
        info={"label": "Version des mentions légales signées"},
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

    reservations = db.relationship(
        "Reservation",
        back_populates="user",
    )
    """ List of reservations made by the user.

    :type: list(:py:class:`collectives.models.reservation.Reservation`)
    """

    payments = db.relationship(
        "Payment", backref="buyer", foreign_keys="[Payment.buyer_id]", lazy=True
    )
    """ List of payments made by the user.

    :type: list(:py:class:`collectives.models.payment.Payment`)
    """

    reported_payments = db.relationship(
        "Payment", backref="reporter", foreign_keys="[Payment.reporter_id]", lazy=True
    )
    """ List of payments reported by the user (that is, manually entered by the user).

    :type: list(:py:class:`collectives.models.payment.Payment`)
    """

    @validates(
        "first_name",
        "last_name",
        "license",
        "license_category",
        "phone",
        "emergency_contact_name",
        "emergency_contact_phone",
    )
    def truncate_string(self, key, value):
        """Truncates too long string.

        Sometimes, espacially with extranet, a value might be too long. This function
        truncates it to not throw an error. The function automatically extract key max
        length. It adds … in the end.

        :param string key: argument name to check.
        :param string value: argument value to check.
        :return: Truncated string.
        :rtype: string
        """
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return value[: max_len - 1] + "…"
        return value

    def save_avatar(self, file):
        """Save an image as user avatar.

        It will both save the files into the file system and save the path into the database.
        If file is None, it will do nothing. It will use Flask-Upload to save the image.

        :param file: request param to be saved.
        :type file: :py:class:`werkzeug.datastructures.FileStorage`
        """
        if file is not None:
            filename = avatars.save(file, name="user-" + str(self.id) + ".")
            self.avatar = filename

    def delete_avatar(self):
        """Remove and dereference an user avatar."""
        if self.avatar:
            os.remove(avatars.path(self.avatar))
            self.avatar = None

    def get_gender_name(self):
        """Get the name of the user gender.

        :return: The name of the user gender. See :py:class:`Gender`
        :rtype: string
        """
        return Gender(self.gender).display_name()

    def check_license_valid_at_time(self, time):
        """Check if the user license is still valid at a given time.

        Test users (:py:attr:`is_test`) are always valid.

        :param time: Time when the validity must be checked.
        :type time: :py:class:`datetime.datetime`
        :return: True if license is valid.
        :rtype: boolean
        """
        if self.is_test:
            # Test users licenses never expire
            return True
        return self.license_expiry_date > time.date()

    def is_youth(self):
        """Check if user license category is one of a youth (between 18 and 25).

        :return: True if user a youth license.
        :rtype: boolean
        """
        return self.license_category in ["J1", "E1"]

    def is_minor(self):
        """Check if user license category is one of a minor (below 18).

        :return: True if user a youth license.
        :rtype: boolean
        """
        return self.license_category in ["J2", "E2"]

    # Roles
    def matching_roles(self, role_ids):
        """Returns filtered user roles against a role types list.

        :param role_ids: Role types that will be extracted.
        :type role_ids: list(:py:class:`collectives.models.role.RoleIds`)
        :return: Filtered User roles.
        :rtype: list(:py:class:`collectives.models.role.Role`)
        """
        return [role for role in self.roles if role.role_id in role_ids]

    def matching_roles_for_activity(self, role_ids, activity_id):
        """Returns filtered user roles against a role types list and an activity.

        :param role_ids: Role types that will be extracted.
        :type role_ids: list(:py:class:`collectives.models.role.RoleIds`).
        :param activity_id: Activity which will be used as a filter.
        :type activity_id: int
        :return: Filtered User roles.
        :rtype: list(:py:class:`collectives.models.role.Role`)
        """
        matching_roles = self.matching_roles(role_ids)
        return [role for role in matching_roles if role.activity_id == activity_id]

    def has_role(self, role_ids):
        """Check if user has at least one of the roles types.

        :param role_ids: Roles that will be tested.
        :type role_ids: list(:py:class:`collectives.models.role.RoleIds`).
        :return: True if user has at least one of the listed roles type.
        :rtype: boolean
        """
        return len(self.matching_roles(role_ids)) > 0

    def has_role_for_activity(self, role_ids, activity_id):
        """Check if user has at least one of the roles types for an activity.

        :param role_ids: Roles that will be tested.
        :type role_ids: list(:py:class:`collectives.models.role.RoleIds`).
        :param activity_id: Activity onto which role should applied.
        :type activity_id: int
        :return: True if user has at least one of the listed roles type for the activity.
        :rtype: boolean
        """
        roles = self.matching_roles(role_ids)
        return any(role.activity_id == activity_id for role in roles)

    def is_admin(self):
        """Check if user has an admin role.

        See :py:attr:`collectives.models.role.RoleIds.Administrator`

        :return: True if user has an admin role.
        :rtype: boolean
        """
        return self.has_role([RoleIds.Administrator])

    def is_moderator(self):
        """Check if user has a moderator role.

        See :py:meth:`collectives.models.role.RoleIds.all_moderator_roles`

        :return: True if user has a moderator role.
        :rtype: boolean
        """
        return self.has_role(RoleIds.all_moderator_roles())

    def is_supervisor(self):
        """Check if user supervises at least one activity.

        See :py:attr:`collectives.models.role.RoleIds.ActivitySupervisor`

        :return: True if user supervises at least one activity.
        :rtype: boolean
        """
        return len(self.get_supervised_activities()) > 0

    def is_technician(self):
        """Check if user has a technician role.

        See :py:attr:`collectives.models.role.RoleIds.Technician`

        :return: True if user has a technician role.
        :rtype: boolean
        """
        return self.has_role([RoleIds.Administrator, RoleIds.Technician])

    def is_hotline(self):
        """Check if user has a hotline role.

        See :py:attr:`collectives.models.role.RoleIds.Hotline`

        :return: True if user has a hotline role.
        :rtype: boolean
        """
        return self.has_role([RoleIds.Administrator, RoleIds.Hotline])

    def is_accountant(self):
        """Check if user has a hotline role.

        See :py:attr:`collectives.models.role.RoleIds.Accountant`

        :return: True if user has an accountant role.
        :rtype: boolean
        """
        return self.has_role([RoleIds.Administrator, RoleIds.Accountant])

    def can_create_events(self):
        """Check if user has a role which allow him to creates events.

        See :py:meth:`collectives.models.role.RoleIds.all_event_creator_roles`

        :return: True if user can create events.
        :rtype: boolean
        """
        return self.has_role(RoleIds.all_event_creator_roles())

    def can_manage_equipment(self):
        """Check if user has an equipment_manager role.

        :return: True if user has an equiment_manager role.
        :rtype: boolean
        """

        return self.has_role(RoleIds.all_equipment_management_roles())

    def can_manage_reservation(self):
        """Check if user has an equipment_manager role.

        :return: True if user has an equiment_manager role.
        :rtype: boolean
        """

        return self.has_role(RoleIds.all_reservation_management_roles())

    def can_lead_activity(self, activity_id):
        """Check if user has a role which allow him to lead a specific activity.

        See :py:meth:`collectives.models.role.RoleIds.all_activity_leader_roles`

        :param activity_id: Activity which will be tested.
        :type activity_id: int
        :return: True if user can lead the activity.
        :rtype: boolean
        """
        return self.has_role_for_activity(
            RoleIds.all_activity_leader_roles(), activity_id
        )

    def can_lead_activities(self, activities):
        """Check if user has a role which allow him to lead all specified activities.

        See :py:meth:`can_lead_activity`

        :param activities: Activities which will be tested.
        :type activities: list(:py:class:`collectives.models.activitytype.ActivityType`)
        :return: True if user can lead all the activities.
        :rtype: boolean
        """
        return all(self.can_lead_activity(a.id) for a in activities)

    def can_colead_any_activity(self, activities):
        """Check if user has a role which allow him to co-lead any of the specified activities.

        :param activities: Activities which will be tested.
        :type activities: list(:py:class:`collectives.models.activitytype.ActivityType`)
        :return: True if user is a trainee for at least one activity
        :rtype: boolean
        """
        return any(
            a for a in activities if self.has_role_for_activity([RoleIds.Trainee], a.id)
        )

    def can_read_other_users(self):
        """Check if user can see another user profile.

        Only users with roles and which have sign confidentiality agreement can look other users profiles.

        :return: True if user is authorized to see other profiles.
        :rtype: boolean
        """
        return self.has_signed_ca() and self.has_any_role()

    def has_any_role(self):
        """Check if user has any specific roles.

        :return: True if user has at least one role.
        :rtype: boolean
        """
        return len(self.roles) > 0

    def has_signed_ca(self):
        """Check if user has signed the confidentiality agreement.

        :return: True if user has signed it.
        :rtype: boolean
        """
        return self.confidentiality_agreement_signature_date is not None

    def has_signed_legal_text(self):
        """Check if user has signed the current legal text.

        :return: True if user has signed it.
        :rtype: boolean
        """
        is_signed = self.legal_text_signature_date is not None

        current_version = current_app.config["CURRENT_LEGAL_TEXT_VERSION"]
        is_good_signed_version = self.legal_text_signed_version == current_version

        return is_signed and is_good_signed_version

    def supervises_activity(self, activity_id):
        """Check if user supervises a specific activity.

        :param activity_id: Activity which will be tested.
        :type activity_id: int
        :return: True if user supervises the activity.
        :rtype: boolean
        """
        return self.has_role_for_activity([RoleIds.ActivitySupervisor], activity_id)

    def led_activities(self):
        """Get activities the user can lead.

        :return: The list of activities the user can lead.
        :rtype: set(:py:class:`collectives.models.activitytype.ActivityType`)
        """
        roles = self.matching_roles(RoleIds.all_activity_leader_roles())
        return set(role.activity_type for role in roles)

    # Format

    def full_name(self):
        """Get user full name.

        :rtype: String
        """
        return f"{self.first_name} {self.last_name.upper()}"

    def abbrev_name(self):
        """Get user first name and first letter of last name.

        :rtype: String
        """
        return f"{self.first_name} {self.last_name[0].upper()}"

    def get_supervised_activities(self):
        """Get activities the user supervises.

        Admin and President supervise all.

        :rtype: list(:py:class:`collectives.models.activitytype.ActivityType`)
        """
        if self.is_admin() or self.has_role([RoleIds.President]):
            return ActivityType.query.order_by(ActivityType.order).all()

        roles = self.matching_roles([RoleIds.ActivitySupervisor])
        return [role.activity_type for role in roles]

    @property
    def is_active(self):
        """Check if user is currently active.

        An active user is not disabled and its license is valid.

        :return: True if user is active.
        :rtype: boolean
        """
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
