"""Module for user badges related classes
"""
import builtins
from collectives.models.activity_type import ActivityType
from collectives.models.utils import ChoiceEnum
from collectives.models.globals import db


class BadgeIds(ChoiceEnum):
    """Enum listing the type of a badge"""

    # pylint: disable=invalid-name
    Benevole = 1

    @classmethod
    def display_names(cls):
        """Display name of the current badge

        :return: badge name
        :rtype: string
        """
        return {
            cls.Benevole: "Bénévole",
        }

    @classmethod
    def get(cls, required_id):
        """
        :return: Get a :py:class:`BadgeIds` from its id
        :rtype: :py:class:`BadgeIds`
        """
        for badge_id in cls:
            if badge_id == int(required_id):
                return badge_id
        raise builtins.Exception(f"Unknown badge id {required_id}")

    @classmethod
    def get_all(cls):
        """
        :return: :py:class:`BadgeIds` full list
        :rtype: list(:py:class:`BadgeIds)`
        """
        return cls


class Badge(db.Model):
    """Badge for a specific user.

    These objects are linked to :py:class:`collectives.models.user.User` and
    to a :py:class:`collectives.models.activity_type.ActivityType`.
    A same user can have several badges, including on the same activity type.

    Roles are stored in SQL table ``badges``.
    """

    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    """ Database primary key

    :type: int"""

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    """ ID of the user to which the badge is applied.

    :type: int"""

    activity_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), nullable=True, index=True
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

    expiration_date = db.Column(
        db.Date(),
        info={
            "label": "Date d'expiration du badge (par défaut: le 30/09 de l'année en cours)"
        },
    )
    """ Date at which this badge will expire

    :type: :py:class:`datetime.date`"""

    level = db.Column(db.Integer, info={"label": "niveau du badge"})

    """
    Level of the badge. Depending of the type of badge, might be:
    level of expertise, nb of absences,...

    :type: int
    """

    @property
    def name(self):
        """Returns the name of the badge.

        :return: name of the badge.
        :rtype: string
        """

        return BadgeIds(self.badge_id).display_name()

    @property
    def activity_name(self):
        """Returns the name of the corresponding activity

        :return: name of the corresponding activity
        :rtype: string
        """

        return [
            activity_type.name
            for activity_type in ActivityType.get_all_types()
            if activity_type.id == self.activity_id
        ][0]
