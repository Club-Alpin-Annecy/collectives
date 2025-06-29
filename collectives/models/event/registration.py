"""Module for all Event methods related to registration manipulation and check."""

from typing import List
from datetime import datetime
from operator import attrgetter

from collectives.models.registration import (
    Registration,
    RegistrationLevels,
    RegistrationStatus,
)
from collectives.models.globals import db


class DuplicateRegistrationError(RuntimeError):
    """Exception raised when a concurrent registration makes another one a duplicate"""

    pass


class OverbookedRegistrationError(RuntimeError):
    """Exception raised when a concurrent registration makes another one overbooked"""

    pass


class EventRegistrationMixin:
    """Part of Event class for registration manipulation and check.

    Not meant to be used alone."""

    def has_valid_slots(self) -> bool:
        """Check if this event does not have more online slots than overall
        slots.

        :return: True if event has a good configuration of num_slots.
        """
        # pylint: disable=C0301
        return self.num_online_slots >= 0 and self.num_slots >= self.num_online_slots

    def is_registration_open_at_time(self, time: datetime) -> bool:
        """Check if online registration for this event is open.

        :param time: Time that will be checked (usually, current time).
        :return: True if registration is open at ``time``
        """
        if self.registration_open_time is None or self.registration_close_time is None:
            return False
        # pylint: disable=C0301
        return self.registration_open_time <= time <= self.registration_close_time

    def active_registrations(self) -> List[Registration]:
        """Returns all actives registrations.

        See :py:meth:`collectives.models.registration.Registration.is_active`

        :return: All registration of this event which are active
        """
        return [r for r in self.registrations if r.is_active()]

    def active_registrations_with_level(
        self, level: RegistrationLevels
    ) -> List[Registration]:
        """
        :return Active registrations with a given registration level.
        """
        return [r for r in self.active_registrations() if r.level == level]

    def active_normal_registrations(self) -> List[Registration]:
        """
        :return Active registrations with a "normal" level.
        """
        return self.active_registrations_with_level(RegistrationLevels.Normal)

    def holding_slot_registrations(self) -> List[Registration]:
        """Returns all holding slot registrations.

        See :py:meth:`collectives.models.registration.Registration.is_holding_slot`

        :return: All registration of this event which are valid
        """
        return [r for r in self.registrations if r.is_holding_slot()]

    def waiting_registrations(self) -> List[Registration]:
        """Returns all waiting list registrations.

        See :py:meth:`collectives.models.registration.RegistrationStatus.Waiting`

        :return: All registration of this event which are waiting, ordered.
        """
        waiting = [
            r for r in self.registrations if r.status == RegistrationStatus.Waiting
        ]
        waiting.sort(key=attrgetter("id"))
        return waiting

    def num_taken_slots(self) -> int:
        """Return the number of slots that have been taken

        (registrations that are either active or pending, plus
        number of leaders if requested)

        :return: count of taken slots
        """
        taken_count = sum(
            1 for registration in self.registrations if registration.is_holding_slot()
        )
        if self.include_leaders_in_counts:
            taken_count += len(self.leaders)
        return taken_count

    def num_pending_registrations(self) -> int:
        """Return the number of pending registrations
        (registrations that are holding a slot but not active yet)

        :return: count of pending slots
        """
        return sum(
            1
            for registration in self.registrations
            if (registration.is_holding_slot() and not registration.is_active())
        )

    def num_waiting_registrations(self) -> int:
        """Return the number of registrations in witing list"""
        return sum(
            1
            for registration in self.registrations
            if registration.status == RegistrationStatus.Waiting
        )

    def has_free_slots(self) -> bool:
        """Check if this event is full.

        :return: True if there is less active registrations than available slots.
        """
        return self.num_taken_slots() < self.num_slots

    def has_free_online_slots(self) -> bool:
        """Check if an user can self-register.

        :return: True if there is less active registrations than available
                online slots.
        """
        return self.num_taken_slots() < self.num_online_slots

    def has_free_waiting_slots(self) -> bool:
        """Check if an user can self-register to the waiting list.

        :return: True if there is less waiting registrations than available
                wainting slots.
        :rtype: boolean
        """
        return self.num_waiting_registrations() < self.num_waiting_list

    def free_slots(self) -> bool:
        """Calculate the amount of available slot for new registrations.

        :return: Number of free slots for this event.
        """
        free = self.num_slots - self.num_taken_slots()
        return max(free, 0)

    def existing_registrations(
        self, user: "collectives.models.user.User"
    ) -> List[Registration]:
        """
        Returns all existing registrations of a given user for this event
        :param user: User which will be tested.
        :return: List of existing registrations
        """
        return [
            registration
            for registration in self.registrations
            if registration.user_id == user.id
        ]

    def is_registered(self, user: "collectives.models.user.User") -> bool:
        """Check if a user is registered to this event.

        Note:
        - leader is not considered as registered.
        - a rejected user user is still considered as registered.

        :param user: User which will be tested.
        :return: True if user is registered.
        """
        return any(self.existing_registrations(user))

    def is_registered_with_status(
        self, user: "collectives.models.user.User", statuses: List[RegistrationStatus]
    ) -> bool:
        """Check if a user is registered to this event with specific status.

        Note:
        - leader is not considered as registered.

        :param user: User which will be tested.
        :param statuses: Status acceptable to test registrations.
        :return: True if user is registered with a specific status
        """
        return any(
            registration
            for registration in self.registrations
            if registration.user_id == user.id and registration.status in statuses
        )

    def is_rejected(self, user: "collectives.models.user.User") -> bool:
        """Check if a user is rejected on this event.

        :param user: User which will be tested.
        :return: True if user is registered with a ``rejected`` status
        """
        return self.is_registered_with_status(user, (RegistrationStatus.Rejected,))

    def is_unregistered(self, user: "collectives.models.user.User") -> bool:
        """Check if a user has unregistered this event.

        :param user: User which will be tested.
        :return: True if user is registered with a ``unregistered`` status
        """
        return self.is_registered_with_status(
            user,
            (
                RegistrationStatus.SelfUnregistered,
                RegistrationStatus.LateSelfUnregistered,
            ),
        )

    def is_late_unregistered(self, user: "collectives.models.user.User"):
        """Check if a user has unregistered lately this event.

        :param user: User which will be tested.
        :return: True if user is registered with a ``late unregistered`` status
        """
        return self.is_registered_with_status(
            user, (RegistrationStatus.LateSelfUnregistered,)
        )

    def is_in_late_unregistration_period(
        self, user: "collectives.models.user.User"
    ) -> bool:
        """
        :returns: whether `user` unregistering now should be considered "late"
        """
        return any(
            reg.is_in_late_unregistration_period()
            for reg in self.existing_registrations(user)
        )

    def is_user_in_user_group(self, user: "collectives.models.user.User") -> bool:
        """Check if a user is part of the event user group

        :param user: User which will be tested.
        :return: True if there is no user group or the user is a member of the group
        """

        if self.user_group is None:
            return True
        return self.user_group.contains(user, time=self.event.start)

    def can_self_register(
        self,
        user: "collectives.models.user.User",
        time: datetime,
        waiting: bool = False,
    ) -> bool:
        """Check if a user can self-register.

        An user can self-register if:
          - their phone number is valid
          - their emergency phone number is valid
          - they have no current registration with this event.
          - they are not a leader of this event.
          - given time parameter (usually current_time) is in registration
            time.
          - there are available online slots
          - user is registered to the parent event if any
          - user license is compatible with event type
          - user does not have a valid Suspended badge

        :param user: User which will be tested.
        :param time: Time that will be checked (usually, current time).
        :param waiting: check if user can self register into waiting list
        :return: True if user can self-register.
        """
        if not user.is_active:
            return False
        if not user.has_valid_phone_number():
            return False
        if not user.has_valid_phone_number(emergency=True):
            return False
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
        if user.has_a_valid_suspended_badge():
            return False
        if not waiting:
            return self.has_free_online_slots()
        if self.has_free_online_slots():
            return False
        return len(self.waiting_registrations()) < self.num_waiting_list

    def can_self_unregister(
        self, user: "collectives.models.user.User", time: datetime
    ) -> bool:
        """Check if a user can self-unregister.

        An user can self-register if:
          - they have an Active, PaymentPending or Waiting registration
          - event is in the future

        :param user: User which will be tested.
        :param time: Time that will be checked (usually, current time).
        :return: True if user can self-register.
        """
        if time > self.start:
            return False

        good_statuses = (
            RegistrationStatus.PaymentPending,
            RegistrationStatus.Active,
            RegistrationStatus.Waiting,
        )

        return self.is_registered_with_status(user, good_statuses)

    def add_registration_check_race_conditions(
        self, registration: Registration, allow_overbooking: bool = False
    ):
        """Add a registration to an event, checking for possible race conditions.

        :raises DuplicateRegistrationError: If another registration exists for the same user
        :raises OverbookedRegistrationError: If the event was already full by the time this
          registration was committed

        :param registration: Registration to attempt to add to this event
        :param allow_overbooking: If true, to not check for overbooking race conditions
        """
        self.registrations.append(registration)
        db.session.commit()

        db.session.expire(self)
        if registration.is_duplicate():
            self.registrations.remove(registration)
            db.session.delete(registration)
            db.session.commit()
            raise DuplicateRegistrationError("Vous êtes déjà inscrit(e).")
        if not allow_overbooking and registration.is_overbooked():
            self.registrations.remove(registration)
            db.session.delete(registration)
            db.session.commit()
            raise OverbookedRegistrationError("L'événement est déjà complet.")
