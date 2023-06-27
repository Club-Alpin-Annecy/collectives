""" Module for all User methods related to badge manipulation and check."""


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

    def is_benevole(self):
        """Check if user has a benevole badge.

        :return: True if user has a benevole badge.
        :rtype: boolean
        """
        return self.has_badge([BadgeIds.Benevole])
