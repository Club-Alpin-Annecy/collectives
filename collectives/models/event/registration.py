""" Module for all Event methods related to registration manipulation and check."""

from operator import attrgetter

from collectives.models.registration import RegistrationLevels, RegistrationStatus


class EventRegistrationMixin:
    """Part of Event class for registration manipulation and check.

    Not meant to be used alone."""

    def has_valid_slots(self):
        """Check if this event does not have more online slots than overall
        slots.

        :return: True if event has a good configuration of num_slots.
        :rtype: boolean
        """
        # pylint: disable=C0301
        return self.num_online_slots >= 0 and self.num_slots >= self.num_online_slots

    def is_registration_open_at_time(self, time):
        """Check if online registration for this event is open.

        :param time: Time that will be checked (usually, current time).
        :type time: :py:class:`datetime.datetime`
        :return: True if registration is open at ``time``
        :rtype: boolean
        """
        if self.registration_open_time is None or self.registration_close_time is None:
            return False
        # pylint: disable=C0301
        return self.registration_open_time <= time <= self.registration_close_time

    def active_registrations(self):
        """Returns all actives registrations.

        See :py:meth:`collectives.models.registration.Registration.is_active`

        :return: All registration of this event which are active
        :rtype: list(:py:class:`collectives.models.registration.Registration`)
        """
        return [r for r in self.registrations if r.is_active()]

    def active_registrations_with_level(self, level):
        """
        :return Active registrations with a given registration level.
        :rtype: list(:py:class:`collectives.models.registration.Registration`)
        """
        return [r for r in self.active_registrations() if r.level == level]

    def active_normal_registrations(self):
        """
        :return Active registrations with a "normal" level.
        :rtype: list(:py:class:`collectives.models.registration.Registration`)
        """
        return self.active_registrations_with_level(RegistrationLevels.Normal)

    def holding_slot_registrations(self):
        """Returns all holding slot registrations.

        See :py:meth:`collectives.models.registration.Registration.is_holding_slot`

        :return: All registration of this event which are valid
        :rtype: list(:py:class:`collectives.models.registration.Registration`)
        """
        return [r for r in self.registrations if r.is_holding_slot()]

    def waiting_registrations(self):
        """Returns all waiting list registrations.

        See :py:meth:`collectives.models.registration.RegistrationStatus.Waiting`

        :return: All registration of this event which are waiting, ordered.
        :rtype: list(:py:class:`collectives.models.registration.Registration`)
        """
        waiting = [
            r for r in self.registrations if r.status == RegistrationStatus.Waiting
        ]
        waiting.sort(key=attrgetter("id"))
        return waiting

    def num_taken_slots(self):
        """Return the number of slots that have been taken
        (registration is either active or pending)

        :return: count of taken slots
        :rtype: int
        """
        return len(
            [
                registration
                for registration in self.registrations
                if registration.is_holding_slot()
            ]
        )

    def num_pending_registrations(self):
        """Return the number of pending registrations
        (registrations that are holding a slot but not active yet)

        :return: count of pending slots
        :rtype: int
        """
        return len(
            [
                registration
                for registration in self.registrations
                if (registration.is_holding_slot() and not registration.is_active())
            ]
        )

    def has_free_slots(self):
        """Check if this event is full.

        :return: True if there is less active registrations than available slots.
        :rtype: boolean
        """
        return self.num_taken_slots() < self.num_slots

    def has_free_online_slots(self):
        """Check if an user can self-register.

        :return: True if there is less active registrations than available
                online slots.
        :rtype: boolean
        """
        return self.num_taken_slots() < self.num_online_slots

    def has_free_waiting_slots(self):
        """Check if an user can self-register to the waiting list.

        :return: True if there is less waiting registrations than available
                wainting slots.
        :rtype: boolean
        """
        return len(self.waiting_registrations()) < self.num_waiting_list

    def free_slots(self):
        """Calculate the amount of available slot for new registrations.

        :return: Number of free slots for this event.
        :rtype: int"""
        free = self.num_slots - self.num_taken_slots()
        return max(free, 0)

    def existing_registrations(self, user):
        """
        Returns all existing registrations of a given user for this event
        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: List of existing registrations
        :rtype: :py:class:`collectives.models.registration.Registration`
        """
        return [
            registration
            for registration in self.registrations
            if registration.user_id == user.id
        ]

    def is_registered(self, user):
        """Check if a user is registered to this event.

        Note:
        - leader is not considered as registered.
        - a rejected user user is still considered as registered.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user is registered.
        :rtype: boolean
        """
        return any(self.existing_registrations(user))

    def is_registered_with_status(self, user, statuses):
        """Check if a user is registered to this event with specific status.

        Note:
        - leader is not considered as registered.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :param statuses: Status acceptable to test registrations.
        :type statuses: list(:py:class:`collectives.models.registration.RegistrationStatus`)
        :return: True if user is registered with a specific status
        :rtype: boolean
        """
        existing_registrations = [
            registration
            for registration in self.registrations
            if registration.user_id == user.id and registration.status in statuses
        ]
        return any(existing_registrations)

    def is_rejected(self, user):
        """Check if a user is rejected on this event.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user is registered with a ``rejected`` status
        :rtype: boolean
        """
        return self.is_registered_with_status(user, [RegistrationStatus.Rejected])

    def is_unregistered(self, user):
        """Check if a user has unregistered this event.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user is registered with a ``unregistered`` status
        :rtype: boolean
        """
        return self.is_registered_with_status(
            user, [RegistrationStatus.SelfUnregistered]
        )

    def is_user_in_user_group(self, user: "collectives.models.user.User") -> bool:
        """Check if a user is part of the event user group

        :param user: User which will be tested.
        :return: True if there is no user group or the user is a member of the group
        :rtype: boolean
        """

        # Migrate to new version of attribute
        self.migrate_parent_event_id()

        if self.user_group is None:
            return True
        return self.user_group.contains(user)

    def can_self_register(self, user, time, waiting=False):
        """Check if a user can self-register.

        An user can self-register if:
          - they have no current registration with this event.
          - they are not a leader of this event.
          - given time parameter (usually current_time) is in registration
            time.
          - there are available online slots
          - user is registered to the parent event if any
          - user license is compatible with event type

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :param time: Time that will be checked (usually, current time).
        :type time: :py:class:`datetime.datetime`
        :param waiting: check if user can self register into waiting list
        :type time: boolean
        :return: True if user can self-register.
        :rtype: boolean
        """
        if not self.is_confirmed():
            return False
        if self.is_leader(user) or self.is_registered(user):
            return False
        if not self.is_user_in_user_group(user):
            return False
        if not self.is_registration_open_at_time(time):
            return False
        if not self.event_type.has_valid_license(user):
            return False
        if not waiting:
            return self.has_free_online_slots()
        if self.has_free_online_slots():
            return False
        return len(self.waiting_registrations()) < self.num_waiting_list
