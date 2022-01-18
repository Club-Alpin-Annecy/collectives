"""Module to describe the type of activity.
"""
from sqlalchemy.orm import validates
from flask import escape

from .globals import db


class ActivityType(db.Model):
    """Class of the type of activity.

    An activity type can be a sport (climbing, hiking) or another occupation
    (training). Persistence is done with SQLAlchemy and in the table
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

    trigram = db.Column(db.String(8), nullable=False)
    """ Three-letter code.

    Mainly used to identify activity type in payment order references

    :type: string
    """

    order = db.Column(db.Integer, nullable=False)
    """ Order to display this activity

    :type: int
    """

    # Relationships
    persons = db.relationship("Role", backref="activity_type", lazy=True)
    """Person with a role with this activity

    :type: :py:class:`collectives.models.user.User`
    """

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
    def get_all_types(cls):
        """List all activity_types in database

        :return: list of types
        :rtype: list(:py:class:`ActivityType`)"""
        return cls.query.order_by("order", "name").all()

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
