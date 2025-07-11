"""Module for all User methods related to role manipulation and check."""

from typing import List, Set
import datetime

from collectives.models.globals import db
from collectives.models.activity_type import ActivityType
from collectives.models.role import Role, RoleIds


class UserRoleMixin:
    """Part of User related to role.

    Not meant to be used alone."""

    def matching_roles(self, role_ids: List[RoleIds]) -> List[Role]:
        """Returns filtered user roles against a role types list.

        :param role_ids: Role types that will be extracted.
        :return: Filtered User roles.
        """
        return [role for role in self.roles if role.role_id in role_ids]

    def matching_roles_for_activity(
        self, role_ids: List[RoleIds], activity_id: int
    ) -> List[Role]:
        """Returns filtered user roles against a role types list and an activity.

        :param role_ids: Role types that will be extracted.
        :param activity_id: Activity which will be used as a filter.
        :return: Filtered User roles.
        """
        matching_roles = self.matching_roles(role_ids)
        return [role for role in matching_roles if role.activity_id == activity_id]

    def has_role(self, role_ids: List[RoleIds]) -> bool:
        """Check if user has at least one of the roles types.

        :param role_ids: Roles that will be tested.
        :return: True if user has at least one of the listed roles type.
        """
        return len(self.matching_roles(role_ids)) > 0

    def has_role_for_activity(self, role_ids: List[RoleIds], activity_id: int):
        """Check if user has at least one of the roles types for an activity.

        :param role_ids: Roles that will be tested.
        :param activity_id: Activity onto which role should applied.
        :return: True if user has at least one of the listed roles type for the activity.
        """
        roles = self.matching_roles(role_ids)
        return any(role.activity_id == activity_id for role in roles)

    def is_admin(self) -> bool:
        """Check if user has an admin role.

        See :py:attr:`collectives.models.role.RoleIds.Administrator`

        :return: True if user has an admin role.
        """
        return self.has_role([RoleIds.Administrator])

    def is_moderator(self) -> bool:
        """Check if user has a moderator role.

        See :py:meth:`collectives.models.role.RoleIds.all_moderator_roles`

        :return: True if user has a moderator role.
        """
        return self.has_role(RoleIds.all_moderator_roles())

    def is_supervisor(self) -> bool:
        """Check if user supervises at least one activity.

        See :py:attr:`collectives.models.role.RoleIds.ActivitySupervisor`

        :return: True if user supervises at least one activity.
        """
        return len(self.get_supervised_activities()) > 0

    def is_technician(self) -> bool:
        """Check if user has a technician role.

        See :py:attr:`collectives.models.role.RoleIds.Technician`

        :return: True if user has a technician role.
        """
        return self.has_role([RoleIds.Administrator, RoleIds.Technician])

    def is_hotline(self) -> bool:
        """Check if user has a hotline role.

        See :py:attr:`collectives.models.role.RoleIds.Hotline`

        :return: True if user has a hotline role.
        """
        return self.has_role([RoleIds.Administrator, RoleIds.Hotline])

    def is_accountant(self) -> bool:
        """Check if user has a hotline role.

        See :py:attr:`collectives.models.role.RoleIds.Accountant`

        :return: True if user has an accountant role.
        """
        return self.has_role([RoleIds.Administrator, RoleIds.Accountant])

    def can_create_events(self) -> bool:
        """Check if user has a role which allow him to creates events.

        See :py:meth:`collectives.models.role.RoleIds.all_event_creator_roles`

        :return: True if user can create events.
        """
        return self.has_role(RoleIds.all_event_creator_roles())

    def can_manage_equipment(self) -> bool:
        """Check if user has an equipment_manager role.

        :return: True if user has an equiment_manager role.
        """

        return self.has_role(RoleIds.all_equipment_management_roles())

    def can_manage_reservation(self) -> bool:
        """Check if user has an equipment_manager role.

        :return: True if user has an equiment_manager role.
        """

        return self.has_role(RoleIds.all_reservation_management_roles())

    def can_create_reservation(self) -> bool:
        """Check if user has role to create reservations
        :return: True if user can create reservations
        """
        return self.has_role(RoleIds.all_reservation_creator_roles())

    def is_leader(self) -> bool:
        """Check if user has a role which allow him to lead at least one activity.

        See :py:meth:`collectives.models.role.RoleIds.all_activity_leader_roles`

        :return: True if user can lead at least one activity.
        """
        return self.has_role(RoleIds.all_activity_leader_roles())

    def can_lead_activity(self, activity: ActivityType) -> bool:
        """Check if user has a role which allow him to lead a given activity.

        See :py:meth:`collectives.models.role.RoleIds.all_activity_leader_roles`

        :param activity: Activity which will be tested.
        :return: True if user can leadthe activity.
        """
        return self.has_role_for_activity(
            RoleIds.all_activity_leader_roles(), activity.id
        )

    def can_colead_any_activity(self, activities: List[ActivityType]) -> bool:
        """Check if user has a role which allow him to co-lead any of the specified activities.

        :param activities: Activities which will be tested.
        :return: True if user is a trainee for at least one activity
        """
        return any(
            a for a in activities if self.has_role_for_activity([RoleIds.Trainee], a.id)
        )

    def can_read_other_users(self) -> bool:
        """Check if user can see another user profile.

        Only users with roles and which have sign confidentiality agreement can look other users
        profiles.

        :return: True if user is authorized to see other profiles.
        """
        return self.has_signed_ca() and self.has_any_role()

    def has_any_role(self) -> bool:
        """Check if user has any specific roles.

        :return: True if user has at least one role.
        """
        return len(self.roles) > 0

    def supervises_activity(self, activity_id: int) -> bool:
        """Check if user supervises a specific activity.

        :param activity_id: Activity which will be tested.
        :return: True if user supervises the activity.
        """
        return self.has_role_for_activity([RoleIds.ActivitySupervisor], activity_id)

    def can_manage_all_activities(self) -> bool:
        """Admins and Presidents can manage all activities."""
        return self.is_admin() or self.has_role([RoleIds.President])

    def can_lead_on(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
        excluded_event_id: List[int] = None,
    ) -> bool:
        """Check if user is already leading an event on a specified timespan.
        The check only considers events that require an activity (e.g 'Collectives'
        but not 'Soirées')

        :param start: Start of the timespan
        :param end: End of the timespan
        :param excluded_event_id: Event id to exclude (often the event being edited)
        :return: True if user can lead on the specified timespan.
        """
        # pylint: disable=(import-outside-toplevel
        from collectives.models.event import Event, EventType

        query = db.session.query(Event)
        query = query.filter(Event.start < end)
        query = query.filter(Event.end > start)
        query = query.filter(Event.leaders.contains(self))
        query = query.filter(Event.id != excluded_event_id)
        # pylint: disable=comparison-with-callable
        query = query.filter(EventType.id == Event.event_type_id)
        # pylint: enable=comparison-with-callable
        query = query.filter(EventType.requires_activity == True)
        events = query.all()

        return not any(event.is_confirmed() for event in events)

    def get_organizable_activities(
        self, need_leader: bool = False
    ) -> Set[ActivityType]:
        """Get activities the user can lead or organize.

        :param need_leader: If True, requires a "leader" role,
          otherwise an "organizer" role suffices.
        :return: The list of activities the user can lead.
        """
        ok_roles = (
            RoleIds.all_activity_leader_roles()
            if need_leader
            else RoleIds.all_activity_organizer_roles()
        )
        user_roles = self.matching_roles(ok_roles)
        return set(role.activity_type for role in user_roles)

    def get_supervised_activities(self) -> Set[ActivityType]:
        """Get set of activities the user supervises.

        Admin and President supervise all.
        """
        if self.can_manage_all_activities():
            return ActivityType.get_all_types(include_deprecated=True)

        roles = self.matching_roles([RoleIds.ActivitySupervisor])
        return [role.activity_type for role in roles]

    def activities_with_role(self) -> Set[ActivityType]:
        """
        :return: The set of activities for which the user has a role
        """
        return set(
            role.activity_type for role in self.roles if role.activity_type is not None
        )
