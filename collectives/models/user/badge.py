""" Module for all User methods related to badge manipulation and check."""


from datetime import date
from collectives.models.badge import BadgeIds


class UserBadgeMixin:
    """Part of User related to badge.

    Not meant to be used alone."""

    def matching_badges(self, badge_ids):
        """Returns filtered user badges against a badge types list.

        :param badge_ids: Role types that will be extracted.
        :type badge_ids: list(:py:class:`collectives.models.badge.BadgeIds`)
        :return: Filtered User badges.
        :rtype: list(:py:class:`collectives.models.badge.Badge`)
        """
        return [badge for badge in self.badges if badge.badge_id in badge_ids]

    def has_badge(self, badge_ids):
        """Check if user has at least one of the badges types.

        :param badge_ids: badges that will be tested.
        :type badge_ids: list(:py:class:`collectives.models.badge.RoleIds`).
        :return: True if user has at least one of the listed badges type.
        :rtype: boolean
        """
        return len(self.matching_badges(badge_ids)) > 0

    def has_a_valid_badge(self, badge_ids):
        """Check if user has at least one of the badges types
        with a valid expiration date.

        :param badge_ids: badges that will be tested.
        :type badge_ids: list(:py:class:`collectives.models.badge.RoleIds`).
        :return: True if user has at least one of the listed badges type
        with a valid expiration date.
        :rtype: boolean
        """
        badges = self.matching_badges(badge_ids)
        expirations = [
            badge for badge in badges if badge.expiration_date > date.today()
        ]
        return len(expirations) > 0

    def has_a_valid_benevole_badge(self):
        """Check if user has a benevole badge.

        :return: True if user has a benevole badge.
        :rtype: boolean
        """
        return self.has_a_valid_badge([BadgeIds.Benevole])

    def has_badge_for_activity(self, badge_ids, activity_id):
        """Check if user has at least one of the badge types for an activity.

        :param badge_ids: Badges that will be tested.
        :type badge_ids: list(:py:class:`collectives.models.badge:BadgeIds`).
        :param activity_id: Activity onto which role should applied.
        :type activity_id: int
        :return: True if user has at least one of the listed roles type for the activity.
        :rtype: boolean
        """
        badges = self.matching_badges(badge_ids)
        return any(badge.activity_id == activity_id for badge in badges)

    def has_this_badge_for_activity(self, badge_id, activity_id):
        """Check if user has a specific badge for an activity.

        :param badge_id: Badge that will be tested.
        :type badge_id: :py:class:`collectives.models.badge:BadgeIds`.
        :param activity_id: Activity onto which role should applied.
        :type activity_id: int
        :return: True if user has the corresponding badge type for the activity.
        :rtype: boolean
        """
        badges = self.matching_badges([badge_id])
        return any(badge.activity_id == activity_id for badge in badges)
