""" Module for all User methods related to badge manipulation and check."""

from typing import List, Optional, Set

from collectives.models.badge import Badge, BadgeIds

from collectives.models.activity_type import ActivityType


class UserBadgeMixin:
    """Part of User related to badge.

    Not meant to be used alone."""

    def matching_badges(
        self, badge_ids: List[BadgeIds], valid_only=False
    ) -> List[Badge]:
        """Returns filtered user badges against a badge types list.

        :param badge_ids: Role types that will be extracted.
        :param valid_only: If True, return valid badges only
        :return: Filtered User badges.
        """
        badges = (badge for badge in self.badges if badge.badge_id in badge_ids)

        if not valid_only:
            return list(badges)

        return [badge for badge in badges if not badge.is_expired()]

    def has_badge(self, badge_ids: List[BadgeIds]) -> bool:
        """Check if user has at least one of the badges types.

        :param badge_ids: badges that will be tested.
        :return: True if user has at least one of the listed badges type.
        """
        return len(self.matching_badges(badge_ids)) > 0

    def has_a_valid_badge(self, badge_ids: List[BadgeIds]) -> bool:
        """Check if user has at least one of the badges types
        with a valid expiration date.

        :param badge_ids: badges that will be tested.
        :return: True if user has at least one of the listed badges type
        with a valid expiration date.
        """
        badges = self.matching_badges(badge_ids, valid_only=True)
        return len(badges) > 0

    def has_a_valid_benevole_badge(self) -> bool:
        """Check if user has a benevole badge.

        :return: True if user has a benevole badge.
        """
        return self.has_a_valid_badge([BadgeIds.Benevole])

    def has_badge_for_activity(
        self, badge_ids: List[BadgeIds], activity_id: Optional[int]
    ) -> bool:
        """Check if user has at least one of the badge types for an activity.

        :param badge_ids: Badges that will be tested.
        :param activity_id: Activity onto which role should applied.
        :return: True if user has at least one of the listed roles type for the activity.
        """
        badges = self.matching_badges(badge_ids)
        return any(badge.activity_id == activity_id for badge in badges)

    def has_this_badge_for_activity(
        self, badge_id: BadgeIds, activity_id: Optional[int]
    ) -> bool:
        """Check if user has a specific badge for an activity.

        :param badge_id: Badge that will be tested.
        :param activity_id: Activity onto which role should applied.
        :return: True if user has the corresponding badge type for the activity.
        """
        badges = self.matching_badges([badge_id])
        return any(badge.activity_id == activity_id for badge in badges)

    def activities_with_valid_badge(
        self, badge_ids: List[BadgeIds]
    ) -> Set[ActivityType]:
        """
        Returns the set of activities for which the user has one of the given badges

        :param badge_id: List of badge ids to look for
        :return: The set of activities for which the user has a badge
        """
        badges = self.matching_badges(badge_ids, valid_only=True)
        return set(
            badge.activity_type for badge in badges if badge.activity_type is not None
        )
