"""Module for all User methods related to badge manipulation and check."""

from typing import List, Optional, Set

from datetime import date, timedelta
from collectives.models.badge import Badge, BadgeIds
from collectives.models.registration import Registration
from collectives.models.activity_type import ActivityType
from collectives.models import db
from collectives.models.configuration import Configuration
from collectives.utils.time import current_time


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

    def has_a_valid_suspended_badge(self) -> bool:
        """Check if user has a Suspended badge.

        :return: True if user has a non-expired suspended badge.
        """
        return self.has_a_valid_badge([BadgeIds.Suspended])

    def is_suspended(self) -> bool:
        """Check if a user is suspended.

        :return: True if user is suspended
        """
        return self.has_a_valid_suspended_badge()

    def suspension_end_date(self) -> date:
        """Returns the expiration date if the user is currently suspended,
        ``None`` otherwise
        """
        suspended_badges = self.matching_badges([BadgeIds.Suspended], valid_only=True)
        if not suspended_badges:
            return None
        return max(badge.expiration_date for badge in suspended_badges)

    def number_of_valid_warning_badges(self) -> int:
        """Number of valid warning badges.

        :param badge_ids: badges that will be tested.
        :return: Number of valid warning badges.
        """
        return len(
            self.matching_badges([BadgeIds.UnjustifiedAbsenceWarning], valid_only=True)
        )

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

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def assign_badge(
        self,
        badge_id: BadgeIds,
        expiration_date: date,
        activity_id: Optional[int] = None,
        level: Optional[int] = None,
        registration: Optional[Registration] = None,
    ):
        """Assign a badge to the user.

        :param badge_id: The ID of the badge to be assigned.
        :param expiration_date: The date when the badge will expire.
        :param activity_id: The ID of the activity onto which the badge should be applied.
        """
        badge = Badge(
            user_id=self.id,
            badge_id=badge_id,
            expiration_date=expiration_date,
            activity_id=activity_id,
            level=level,
            registration=registration,
            creation_time=current_time(),
        )
        try:
            db.session.add(badge)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def increment_warning_badges(self, registration: Registration):
        """
        Increment warning badges based on user's conditions and number of warning badges,
        and assign or update the badge with appropriate expiration date and level.
        """

        # Already suspended, do nothing
        if self.is_suspended():
            return

        # There is already a badge associated to this registration
        if any(
            badge
            for badge in registration.badges
            if badge.badge_id
            in (BadgeIds.Suspended, BadgeIds.UnjustifiedAbsenceWarning)
        ):
            return

        # Fetch the number of warning & suspended badges, whether valid or not
        num_valid_warning_badges = len(
            self.matching_badges([BadgeIds.UnjustifiedAbsenceWarning], valid_only=True)
        )
        num_warning_badges = len(
            self.matching_badges([BadgeIds.UnjustifiedAbsenceWarning], valid_only=False)
        )
        num_suspended_badges = len(
            self.matching_badges([BadgeIds.Suspended], valid_only=False)
        )
        # Update badges and expiration dates based on conditions, or continue if nothing to do
        try:
            if num_valid_warning_badges >= Configuration.NUM_WARNINGS_BEFORE_SUSPENSION:
                badge_id = BadgeIds.Suspended
                expiration_date = date.today() + timedelta(
                    weeks=Configuration.SUSPENSION_DURATION
                )
                self.assign_badge(
                    badge_id,
                    expiration_date=expiration_date,
                    level=num_suspended_badges + 1,
                    registration=registration,
                )

            # always add a warning badge as well
            # this simplifies logic when removing badge due to status change
            badge_id = BadgeIds.UnjustifiedAbsenceWarning
            expiration_date = date(
                (
                    date.today().year
                    if date.today().month < Configuration.LICENSE_EXPIRY_MONTH
                    else date.today().year + 1
                ),
                Configuration.LICENSE_EXPIRY_MONTH,
                1,
            ) - timedelta(days=1)
            self.assign_badge(
                badge_id,
                expiration_date=expiration_date,
                level=num_warning_badges + 1,
                registration=registration,
            )
        except ValueError:
            # Badges update should not break unregistration logic
            pass

    def remove_warning_badges(self, registration: Registration):
        """
        Removes warning badges associated to this registration
        """

        registration_badges = [
            badge
            for badge in registration.badges
            if badge.badge_id
            in (BadgeIds.Suspended, BadgeIds.UnjustifiedAbsenceWarning)
        ]

        if not registration_badges:
            return

        if not any(
            badge
            for badge in registration_badges
            if badge.badge_id == BadgeIds.Suspended
        ):
            # If this badge was counted towards a later suspension,
            # Remove the first suspended badge from a later registration
            max_id = max(badge.id for badge in registration_badges)

            later_suspended_badges = [
                badge
                for badge in self.matching_badges([BadgeIds.Suspended], valid_only=True)
                if badge.id > max_id
            ]
            if later_suspended_badges:
                first_suspended_badge = min(
                    later_suspended_badges, key=lambda badge: badge.id
                )
                db.session.delete(first_suspended_badge)

        for badge in registration_badges:
            db.session.delete(badge)
