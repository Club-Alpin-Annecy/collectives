"""Module for all Event methods related to role manipulation and check."""

from typing import List

from collectives.models.activity_type import ActivityType
from collectives.models.event.event_type import EventType
from collectives.models.user import User
from collectives.models.registration import RegistrationLevels
from collectives.utils.time import current_time


class EventRoleMixin:
    """Part of Event related to role.

    Not meant to be used alone."""

    def has_valid_leaders(self):
        """
        :return: True if current leaders can lead all activities. If activities are empty,
                 returns False.
        :seealso: :py:meth:`activities_without_leader`
        """
        return not event_activities_without_leaders(
            self.activity_types, self.leaders, self.event_type
        )

    def ranked_leaders(self):
        """
        :return: the list of leaders in which the main one comes first
        :rtype: list(:py:class:`collectives.models.user.User`)
        """
        main_leader = None
        other_leaders = []
        for leader in self.leaders:
            if leader.id == self.main_leader_id:
                main_leader = leader
            else:
                other_leaders.append(leader)
        if main_leader is None:
            return other_leaders
        return [main_leader] + other_leaders

    def is_leader(self, user):
        """Check if a user is one of this event leaders.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user is a leader.
        :rtype: boolean"""
        return user in self.leaders

    def is_supervisor(self, user):
        """Check if a user is a supervisor of one of the event activities.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user supervises one of the event activities.
        :rtype: boolean
        """
        return any(a for a in self.activity_types if user.supervises_activity(a.id))

    def has_edit_rights(self, user):
        """Check if a user can edit this event.

        Returns true if either:
         - event is WIP (not created yet)
         - user is leader of this event
         - user supervises any of this event activities
         - user is moderator

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user can edit the event.
        :rtype: boolean
        """
        if self.id is None:
            return True

        if not user.is_active:
            return False
        if user.is_moderator():
            return True
        return self.is_leader(user) or self.is_supervisor(user)

    def has_delete_rights(self, user: User) -> bool:
        """Check if a user can delete this event.

        For events in the future, equivalent to :func:`has_edit_rights`
        For past events, needs supervisor or moderator rights

        :param user: User which will be tested.
        :return: True if user can delete the event.
        """

        if self.start > current_time():
            return self.has_edit_rights(user)

        return user.is_moderator() or self.is_supervisor(user)

    def can_remove_leader(self, user, leader):
        """
        Returns true if either:
         - user supervises any of this event activities
         - user is moderator
         - user is leader of this event and is not removing themselves
        """
        if not self.has_edit_rights(user):
            return False
        if user != leader:
            return True

        return user.is_moderator() or self.is_supervisor(user)

    def coleaders(self):
        """
        :return Active registrations with a "Co-leader" level.
        :rtype: list(:py:class:`collectives.models.registration.Registration`)
        """
        return self.active_registrations_with_level(RegistrationLevels.CoLeader)

    def can_be_coleader(self, user):
        """Check if user has a role which allow him to co-lead any of the event activities.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user is a trainee for at least one activity
        :rtype: boolean
        """
        return user.can_colead_any_activity(self.activity_types)


def event_activities_without_leaders(
    activities: List[ActivityType],
    leaders: List[User],
    event_type: EventType,
) -> List[ActivityType]:
    """Check whether all activities of an event have a valid leader.

    :param bool multi_activity_mode: If `False`, check that all `leaders` can lead the
    (single) activitie in `activities`. If `True`, check that each activity in
    `activities` can be lead by one of the `leaders`.
    :param activities: List of activities to check.
    :param leaders: List of leaders.
    :return: whether all tests succeeded
    """

    leader_activities = set.union(
        *(
            leader.get_organizable_activities(need_leader=event_type.requires_activity)
            for leader in leaders
        )
    )
    return list(set(activities) - leader_activities)
