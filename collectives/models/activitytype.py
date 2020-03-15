"""Module to describe the type of activity.
"""
from . import db

class ActivityType(db.Model):
    """ Class of the type of activity.

    An activity type can be a sport (climbing, hiking) or another occupation
    (training). Persistence is done with SQLAlchemy and in the table
    ``activity_types``
    """

    __tablename__ = 'activity_types'

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
    persons = db.relationship('Role', backref='activity_type', lazy=True)
    """Person with a role with this activity

    :type: User
    """

    def can_be_led_by(self, users):
        """Check if at least anyone in a list can lead an event
        of this activity

        :param users: list of user
        :type users: Array[Users]
        :return: if someone in the list can lead this activity
        :rtype: boolean
        """
        for user in users:
            if user.can_lead_activity(self.id):
                return True
        return False
