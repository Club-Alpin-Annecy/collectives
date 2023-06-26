"""Module for user roles related classes
"""
from collectives.models.utils import ChoiceEnum
from collectives.models.globals import db


class BadgeIds(ChoiceEnum):
    """Enum listing the type of a badge"""

    # TODO implements the different type of badges


class Badge(db.Model):
    """Badge for a specific user.

    These objects are linked to :py:class:`collectives.models.user.User` and
    sometimes to a :py:class:`collectives.models.activity_type.ActivityType`.
    A same user can have several badges, including on the same activity type.

    Roles are stored in SQL table ``roles``.
    """

    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    """ Database primary key

    :type: int"""

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    """ ID of the user to which the role is applied.

    :type: int"""

    activity_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), nullable=False, index=True
    )
    """ ID of the activity to which the badge is applied.

    :type: int"""

    badge_id = db.Column(
        db.Enum(BadgeIds),
        nullable=False,
        info={
            "choices": BadgeIds.choices(),
            "coerce": BadgeIds.coerce,
            "label": "Badge",
        },
    )
    """ Type of the badge.

    :type: :py:class:`BadgeIds`
    """

    expiration_date = db.Column(db.Date(), info={"label": "Date d'expiration du badge"})
    """ Date at which this badge will expire

    :type: :py:class:`datetime.date`"""

    level = db.Column(db.Integer, info={"label": "niveau du badge"})

    """
    Level of the badge. Depending of the type of badge, might be: level of expertise, nb of absences,...

    :type: int
    """

    @property
    def name(self):
        """Returns the name of the role.

        :return: name of the role.
        :rtype: string
        """

        return BadgeIds(self.badge_id).display_name()
