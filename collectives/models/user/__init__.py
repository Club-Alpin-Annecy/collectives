"""Module for user related classes

"""
import os

from flask_login import UserMixin
from flask_uploads import UploadSet, IMAGES
import phonenumbers
from collectives.models.reservation import ReservationStatus
from collectives.models.event import Event
from collectives.models.eventtype import EventType

from collectives.models.registration import Registration
from collectives.models.globals import db
from collectives.models.role import RoleIds, Role
from collectives.models.activitytype import ActivityType
from collectives.utils.time import current_time
from collectives.models.configuration import Configuration

from collectives.models.user.enum import Gender
from collectives.models.user.attribute import AttributeUser
from collectives.models.user.relationship import RelationshipUser
from collectives.models.user.role import RoleUser

# Upload
avatars = UploadSet("avatars", IMAGES)


# Models
# pylint: disable=too-many-public-methods
class User(db.Model, UserMixin, AttributeUser, RelationshipUser, RoleUser):
    """Class to manage user.

    Persistence is managed by SQLAlchemy. This class is used by ``flask_login``
    to manage acccess to the system.

    Test users are special users created directly by admin. They have their licence
    validity always true and their personnal information can be modified by
    administrators. The parameter is :py:attr:`is_test`
    """

    __tablename__ = "users"
    """Name of the table for persistence by sqlalchemy"""

    # Relationships

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
        if self.license_expiry_date is None:
            return False
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

        current_version = Configuration.CURRENT_LEGAL_TEXT_VERSION
        is_good_signed_version = self.legal_text_signed_version == current_version

        return is_signed and is_good_signed_version

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
            return ActivityType.get_all_types(True)

        roles = self.matching_roles([RoleIds.ActivitySupervisor])
        return [role.activity_type for role in roles]

    def get_reservations_planned_and_ongoing(self):
        """Get all reservations planned and ongoing from user.

        :rtype: list(:py:class:`collectives.models.reservation.reservations`)
        """
        reservation_list = []
        for reservation in self.reservations:
            if reservation.status in (
                ReservationStatus.Planned,
                ReservationStatus.Ongoing,
            ):
                reservation_list.append(reservation)
        return reservation_list

    def get_reservations_completed(self):
        """Get all reservations completed from user.

        :rtype: list(:py:class:`collectives.models.reservation.reservations`)
        """
        reservation_list = []
        for reservation in self.reservations:
            if reservation.status == ReservationStatus.Completed:
                reservation_list.append(reservation)
        return reservation_list

    @property
    def is_active(self):
        """Check if user is currently active.

        An active user is not disabled and its license is valid.

        :return: True if user is active.
        :rtype: boolean
        """
        return self.enabled and self.check_license_valid_at_time(current_time())

    def has_valid_phone_number(self):
        """Check if the user has a valid phone number.

        Phone numbers are checked using pip phonenumbers.

        :returns: True if user has a valid number
        """
        try:
            number = phonenumbers.parse(self.phone, "FR")
            if not phonenumbers.is_possible_number(number):
                return False
            if not phonenumbers.is_valid_number(number):
                return False

        except phonenumbers.NumberParseException:
            return False
        return True

    def can_register_on(self, start, end, excluded_event_id=None) -> bool:
        """Check if user is already registered to an event on a specified timespan.
        The check only considers events that require an activity (e.g 'Collectives'
        but not 'Soirées')

        :param start: Start of the timespan
        :type start: :py:class:`datetime.datetime`
        :param end: End of the timespan
        :type end: :py:class:`datetime.datetime`
        :param excluded_event_id: Event id to exclude (often the event being edited)
        :type excluded_event_id: int
        :return: True if user can register on the specified timespan.
        :rtype: boolean
        """

        query = db.session.query(Event)
        query = query.filter(Event.start <= end)
        query = query.filter(Event.end >= start)
        query = query.filter(Registration.user_id == self.id)
        # pylint: disable=comparison-with-callable
        query = query.filter(Event.id == Registration.event_id)
        # pylint: disable=comparison-with-callable
        query = query.filter(Event.id != excluded_event_id)
        query = query.filter(EventType.id == Event.event_type_id)
        query = query.filter(EventType.requires_activity == True)
        events = query.all()

        return not any(event.is_confirmed() for event in events)


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
