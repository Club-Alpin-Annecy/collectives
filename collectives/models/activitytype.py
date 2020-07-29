"""Module to describe the type of activity.
"""
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

    order = db.Column(db.Integer, nullable=False)
    """ Order to display this activity

    :type: int
    """

    # Relationships
    persons = db.relationship("Role", backref="activity_type", lazy=True)
    """Person with a role with this activity

    :type: :py:class:`collectives.models.user.User`
    """

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

    def trigram(self):
        """" Assembles a 3 letters activity code by gathering
        first letters from activity name words
        This is not guarranteed to generate unique codes for
        arbitrary inputs, for works well in practice for our activities.

        :return: 3 uppercase laters, e.g. 'SDR' for 'Ski de rando'
        :rtype: string
        """
        tokens = self.name.split(" ")
        if len(tokens) >= 3:
            tri = tokens[0][0] + tokens[1][0] + tokens[2][0]
        elif len(tokens) >= 2:
            tri = tokens[0][0:2] + tokens[1][0]
        else:
            tri = tokens[0][0:3]
        return tri.upper()

    @classmethod
    def get_all_types(cls):
        """List all activity_types in database

        :return: list of types
        :rtype: list(:py:class:`ActivityType`)"""
        return cls.query.order_by("order", "name").all()


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
