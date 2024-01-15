"""Module to describe the type of activity.
"""
from sqlalchemy.orm import validates
from markupsafe import escape

from collectives.models.globals import db


class ActivityType(db.Model):
    """Class of the type of activity.

    An activity type is a sport (climbing, hiking). Previouslu it could
    also be another occupation (training), but this distinction should now
    be made using event types.
    Persistence is done with SQLAlchemy and in the table
    ``activity_types``
    """

    __tablename__ = "activity_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    """ Activity name.

    :type: string
    """

    short = db.Column(db.String(256), nullable=False)
    """ Activity short name.

    It is especially used for icon CSS classes.

    :type: string
    """

    email = db.Column(db.String(256), nullable=True)
    """ Activity dedicated email.

    Mail to be used to send notifications to activity leader.

    :type: string
    """

    trigram = db.Column(db.String(8), nullable=False)
    """ Three-letter code.

    Mainly used to identify activity type in payment order references

    :type: string
    """

    order = db.Column(db.Integer, nullable=False)
    """ Order to display this activity

    :type: int
    """

    deprecated = db.Column(db.Boolean, nullable=False, default=False)
    """ Indicates a deprecated activity type, now replaced by an event type

    Kept in the table for backward compatibility, but excluded from activity lists

    :type: bool
    """

    is_a_service = db.Column(db.Boolean, nullable=True, default=False)
    """ Indicates if activity type corresponds to a service

    :type: bool
    """

    # Relationships
    persons = db.relationship("Role", backref="activity_type", lazy=True)
    """Person with a role with this activity

    :type: :py:class:`collectives.models.user.User`
    """

    # Relationships
    badges = db.relationship("Badge", backref="activity_type", lazy=True)
    """Person with a badge with this activity

    :type: :py:class:`collectives.models.user.User`
    """

    def __str__(self) -> str:
        """Displays the user name."""
        return self.name + f" (ID {self.id})"

    @validates("trigram")
    def truncate_string(self, key, value):
        """Truncates a string to the max SQL field length

        In contrast to one may naively think, trigrams may be longer than three letters.
        Make sure the value is truncated before trying to insert it in base

        :param string key: name of field to validate
        :param string value: tentative value
        :return: Truncated string.
        :rtype: string
        """
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return value[:max_len]
        return value

    def can_be_led_by(self, users):
        """Check if at least anyone in a list can lead an event
        of this activity

        :param users: list of user to test for leading capabilities
        :type users: list[:py:class:`collectives.models.user.User`]
        :return: if someone in the list can lead this activity
        :rtype: boolean
        """
        for user in users:
            if user.can_lead_activity(self.id):
                return True
        return False

    @classmethod
    def get_all_types(cls, include_deprecated=False):
        """List all activity_types in database

        :param include_deprecated: Whether to include deprecated activity types
        :type include_deprecated: bool
        :return: list of types
        :rtype: list(:py:class:`ActivityType`)"""
        query = cls.query.order_by("order", "name")
        if not include_deprecated:
            query = query.filter_by(deprecated=False)
        return query.all()

    @classmethod
    def get(cls, required_id):
        """Get the name of the specified activity id

        :param required_id: the id of the Activity type
        :type required_id: integer
        :return: name of the activity type
        :rtype: :py:class:`ActivityType`"""
        return cls.query.get(required_id)

    @classmethod
    def js_values(cls):
        """Class method to get all actitivity type as js dict

        :return: types as js Dictionnary
        :rtype: String
        """
        types = cls.get_all_types()
        items = [f"{type.id}:'{escape(type.name)}'" for type in types]
        return "{" + ",".join(items) + "}"


def activities_without_leader(activities, leaders):
    """Check if leaders has right to lead it.

    Test each activity to see if at least one leader can lead it (see
    :py:meth:`collectives.models.actitivitytype.ActivityType.can_be_led_by`
    ).
    Return the list of activitiers with no valid leader

    :param leaders: List of User which will be tested.
    :type leaders: list
    :return: True if leaders can lead all activities.
    :rtype: boolean
    """
    return [a for a in activities if not a.can_be_led_by(leaders)]


def leaders_without_activities(activities, leaders):
    """Check if leaders has right to lead it.

    Test each leader to see if they can lead each activity
    :py:meth:`collectives.models.actitivitytype.ActivityType.can_be_led_by`
    ).
    Return the list of leaders not able to lead all activities

    :param leaders: List of User which will be tested.
    :type leaders: list
    :return: True if leaders can lead all activities.
    :rtype: boolean
    """
    return [l for l in leaders if not l.can_lead_activities(activities)]
