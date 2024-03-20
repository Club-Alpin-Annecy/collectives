""" Module for all User methods related to badge manipulation and check."""

from typing import List, Optional

from datetime import date, timedelta
from collectives.models.badge import Badge, BadgeIds
from collectives.models import db


class UserBadgeMixin:
    """Part of User related to badge.

    Not meant to be used alone."""

    def matching_badges(self, badge_ids: List[BadgeIds]) -> List[Badge]:
        """Returns filtered user badges against a badge types list.

        :param badge_ids: Role types that will be extracted.
        :return: Filtered User badges.
        """
        return [badge for badge in self.badges if badge.badge_id in badge_ids]

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
        badges = self.matching_badges(badge_ids)
        expirations = [
            badge for badge in badges if badge.expiration_date > date.today()
        ]
        return len(expirations) > 0

    def has_a_valid_benevole_badge(self) -> bool:
        """Check if user has a benevole badge.

        :return: True if user has a benevole badge.
        """
        return self.has_a_valid_badge([BadgeIds.Benevole])

    def has_a_valid_banned_badge(self) -> bool:
        """Check if user has a benevole badge.

        :return: True if user has a non-expired banned badge.
        """
        return self.has_a_valid_badge([BadgeIds.Banned])

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

    def assign_badge(
        self,
        badge_id: BadgeIds,
        expiration_date: date,
        activity_id: Optional[int] = None,
        level: Optional[int] = None,
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
        )
        try:
            db.session.add(badge)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def update_badge(
        self,
        badge_id: BadgeIds,
        expiration_date: Optional[date] = None,
        activity_id: Optional[int] = None,
        level: Optional[int] = None,
    ):
        """Update a badge for the user.

        :param badge_id: The ID of the badge to be updated.
        :param expiration_date: The date when the badge will expire.
        :param activity_id: The ID of the activity onto which the badge should be applied.
        """
        badge_data = {}
        if expiration_date is not None:
            badge_data["expiration_date"] = expiration_date
        if activity_id is not None:
            badge_data["activity_id"] = activity_id
        if level is not None:
            badge_data["level"] = level

        Badge.query.filter_by(user_id=self.id, badge_id=badge_id).update(badge_data)
        db.session.commit()

    def remove_badge(self, badge_id: BadgeIds):
        """Remove a badge from the user.

        :param badge_id: The ID of the badge to be removed.
        """
        Badge.query.filter_by(user_id=self.id, badge_id=badge_id).delete()
        db.session.commit()

    def update_warning_badges(self):
        """
        Update warning badges based on user's conditions and level,
        and assign or update the badge with appropriate expiration date and level.
        """
        # Check if user has a valid first warning badge
        has_valid_first_warning_badge = self.has_a_valid_badge([BadgeIds.FirstWarning])

        # Check if user has a valid second warning badge
        has_valid_second_warning_badge = self.has_a_valid_badge(
            [BadgeIds.SecondWarning]
        )

        # Update badge and expiration date based on conditions
        if has_valid_second_warning_badge:
            badge_id = BadgeIds.Banned
            expiration_date = date.today() + timedelta(weeks=4)
        elif has_valid_first_warning_badge:
            badge_id = BadgeIds.SecondWarning
            expiration_date = date(
                date.today().year if date.today().month < 10 else date.today().year + 1,
                9,
                30,
            )
        else:
            badge_id = BadgeIds.FirstWarning
            expiration_date = date(
                date.today().year if date.today().month < 10 else date.today().year + 1,
                9,
                30,
            )

        # Check if user already has the badge, if so, update it; if not, assign it
        try:
            if self.has_badge([badge_id]):
                existing_badges = self.matching_badges([badge_id])
                if len(existing_badges) > 1:
                    raise ValueError(f"More than one badge of type {badge_id} exists")

                badge = existing_badges[0]
                new_level = (1 if badge.level is None else badge.level) + 1
                self.update_badge(
                    badge_id, expiration_date=expiration_date, level=new_level
                )
            else:
                self.assign_badge(badge_id, expiration_date=expiration_date, level=1)
        except ValueError:
            # Badges update should not break unregistration logic
            pass
