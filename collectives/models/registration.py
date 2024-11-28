"""Module for registration related classes
"""

from typing import List
from datetime import timedelta
from sqlalchemy.sql import func

from collectives.models.globals import db
from collectives.models.utils import ChoiceEnum
from collectives.models.configuration import Configuration
from collectives.utils.time import current_time


# pylint: disable=invalid-name
class RegistrationLevels(ChoiceEnum):
    """Enum listing acceptable registration levels.

    A registration level is type of event participant, such as a co-leader or a regular
    participant."""

    Normal = 0
    """ Normal participant, no specific power. """

    CoLeader = 1
    """ Participant that will help the event leader."""

    @classmethod
    def display_names(cls):
        """
        :return: a dict defining display names for all enum values
        :rtype: dict
        """
        return {
            cls.Normal: "Participant",
            cls.CoLeader: "Co-encadrant",
        }


class RegistrationStatus(ChoiceEnum):
    """Enum listing acceptable registration status."""

    Active = 0
    """ Registered user is planned to be present. """

    Rejected = 1
    """ Registered user has been rejected by a leader.

    A rejected user shall not be counted in occupied slots, nor be able to register again"""
    PaymentPending = 2
    """ User has initiated but not yet completed payment

    This registration is temporarily holding up a spot, but may be removed after timeout
    """
    SelfUnregistered = 3
    """ User has self unregister to the event.

    User should not be able to register again without leader help."""

    JustifiedAbsentee = 4
    """ User has been absent to the event, but excused by the leader. """

    UnJustifiedAbsentee = 5
    """ User has been absent to the event, but not excused by the leader. """

    ToBeDeleted = 99999
    """ Registration should be deleted. This is not a valid SQL enum entry and should only be used
    as a temporary marker"""

    Waiting = 6
    """ User is in waiting list. """

    Present = 7
    """ User has been present to the event. """

    LateSelfUnregistered = 8
    """ User has self unregister to the event, but late. """
    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls):
        """
        :return: a dict defining display names for all enum values
        :rtype: dict
        """
        return {
            cls.Active: "Inscrit",
            cls.Rejected: "Refusée",
            cls.PaymentPending: "Attente de Paiement",
            cls.SelfUnregistered: "Auto désinscrit",
            cls.LateSelfUnregistered: "Auto désinscrit tardif",
            cls.JustifiedAbsentee: "Absent justifié",
            cls.UnJustifiedAbsentee: "Absent non justifié",
            cls.ToBeDeleted: "Effacer l'inscription",
            cls.Waiting: "Liste d'attente",
            cls.Present: "Présent",
        }

    @classmethod
    def transition_table(cls, requires_payment):
        """
        :return: a dict defining possible transitions for all enum values
        :param bool requires_payment: whether this is a paid event.
        :rtype: dict
        """

        re_register_status = cls.PaymentPending if requires_payment else cls.Active

        return {
            cls.Active: [
                cls.Rejected,
                cls.UnJustifiedAbsentee,
                cls.JustifiedAbsentee,
                cls.Waiting,
                cls.Present,
            ],
            cls.Rejected: [re_register_status, cls.ToBeDeleted, cls.Waiting],
            cls.PaymentPending: [cls.Rejected],
            cls.SelfUnregistered: [
                re_register_status,
                cls.Waiting,
                cls.ToBeDeleted,
                cls.JustifiedAbsentee,
                cls.UnJustifiedAbsentee,
            ],
            cls.JustifiedAbsentee: [cls.Rejected, cls.Active, cls.UnJustifiedAbsentee],
            cls.UnJustifiedAbsentee: [cls.Rejected, cls.Active, cls.JustifiedAbsentee],
            cls.ToBeDeleted: [],
            cls.Waiting: [cls.Rejected, re_register_status],
            cls.Present: [
                cls.Rejected,
                cls.UnJustifiedAbsentee,
                cls.JustifiedAbsentee,
                cls.Waiting,
                cls.Active,
            ],
            cls.LateSelfUnregistered: [
                re_register_status,
                cls.Waiting,
                cls.ToBeDeleted,
                cls.JustifiedAbsentee,
                cls.UnJustifiedAbsentee,
            ],
        }

    def is_valid(self):
        """Checks if registration is valid, ie active or present

        :returns: True or False
        :rtype: bool"""
        return self in RegistrationStatus.valid_status()

    @classmethod
    def valid_status(cls) -> List["RegistrationStatus"]:
        """Returns the list of registration status considered as valid.

        See :py:meth:`collectives.models.registration.RegistrationStatus.is_valid()`"""
        return (RegistrationStatus.Active, RegistrationStatus.Present)

    @classmethod
    def sanctioned_statuses(cls) -> List["RegistrationStatus"]:
        """Returns the list of status thay may trigger sanctions"""
        return (
            RegistrationStatus.UnJustifiedAbsentee,
            RegistrationStatus.LateSelfUnregistered,
        )

    def valid_transitions(self, requires_payment):
        """
        :return: The list of all achievable transitions for a given status (excluding itself)
        :param bool requires_payment: whether this is a paid event.
        :rtype: list[:py:class:`collectives.models.registration.RegistrationStatus`]
        """
        return self.__class__.transition_table(requires_payment)[self.value]


class Registration(db.Model):
    """Object linking a user (participant) and an event.

    Co-leader are also registering. Leader are not registered to their events."""

    __tablename__ = "registrations"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    """ Primary key of the registered user (see  :py:class:`collectives.models.user.User`)

    :type: int"""

    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), index=True)
    """ Primary key of the event to which the user is registered (see
        :py:class:`collectives.models.event.Event`)

    :type: int"""

    status = db.Column(db.Enum(RegistrationStatus), nullable=False)
    """ Status of the registration (active, rejected...)

    :type: :py:class:`collectives.models.registration.RegistrationStatus`"""

    level = db.Column(
        db.Enum(RegistrationLevels), nullable=False
    )  # Co-encadrant, Normal
    """ Level of the participant for this event (normal, co-leader...)

    :type: :py:class:`collectives.models.registration.RegistrationLevels`"""

    is_self = db.Column(db.Boolean, nullable=False, default=True)
    """ Whether this is a self-registration (by the user themselves)

    :type: bool"""

    registration_time = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),  # pylint: disable=not-callable
    )
    """Date of the registration of a user to an event.

    :type: :py:class:`datetime.datetime`"""

    # Relationships

    payments = db.relationship("Payment", backref="registration", lazy=True)
    """ List of payments associated to this registration.

    :type: list(:py:class:`collectives.models.payment.Payment`)
    """

    badges = db.relationship("Badge", back_populates="registration", lazy=True)
    """ List of badges associated to this registration.

    :type: list(:py:class:`collectives.models.badge.Badge`)
    """

    def is_active(self):
        """Check if this registation is active.

        :return: True if :py:attr:`status` is `Active` or `Present` and the user's
                 license has not expired
        :rtype: boolean"""
        if self.is_pending_renewal():
            return False
        if self.status == RegistrationStatus.Active:
            return True
        if self.status == RegistrationStatus.Present:
            return True
        return False

    def is_holding_slot(self):
        """Check if this registation is holding a slot.

        :return: Is :py:attr:`status` active or pending?
        :rtype: boolean"""
        return (
            self.status.is_valid() or self.status == RegistrationStatus.PaymentPending
        )

    def is_rejected(self):
        """Check if this registation is rejected.

        :return: Is :py:attr:`status` rejected ?
        :rtype: boolean"""
        return self.status == RegistrationStatus.Rejected

    def is_unregistered(self):
        """Check if this registation is unregistered.

        :return: Is :py:attr:`status` unregistered ?
        :rtype: boolean"""
        return self.status == RegistrationStatus.SelfUnregistered

    def is_pending_payment(self):
        """Check if this registation is pending payment.

        :return: Is :py:attr:`status` pending payment ?
        :rtype: boolean"""
        return self.status == RegistrationStatus.PaymentPending

    def is_pending_renewal(self):
        """Check if this registation is pending license renewal.

        :return: True if the user's license expires before the end of the event
        :rtype: boolean"""
        return not self.user.check_license_valid_at_time(self.event.end)

    def unsettled_payments(self):
        """Returns the list of unsettled payments associated to this registration

        :return: The list of payments with 'Initiated' status
        :rtype: list[:py:class:`collectives.modes.payment.Payment`]"""
        return [p for p in self.payments if p.is_unsettled()]

    def valid_transitions(self):
        """
        :return: The list of all achievable transitions from the current status
        :rtype: list[:py:class:`collectives.models.registration.RegistrationStatus`]
        """
        return [self.status] + self.status.valid_transitions(
            self.event.requires_payment()
        )

    def _index_in_list(self, regs: List["Registration"]) -> int:
        """Returns the chronlogical place this registration has in a list of registrations.
        -1 if not present. Starts at 0."""
        if self not in regs:
            return -1
        return sum(1 for r in regs if r.id < self.id)

    def holding_index(self) -> int:
        """Returns the chronlogical place this registration has in all holding place registrations.
        -1 if not active. Starts at 0."""
        return self._index_in_list(
            [r for r in self.event.registrations if r.is_holding_slot()]
        )

    def online_index(self) -> int:
        """Returns the chronological place this registration has in all online and holding slot
        registrations. -1 if not holding slot and online. Starts at 0."""
        return self._index_in_list(
            [r for r in self.event.registrations if r.is_self and r.is_holding_slot()]
        )

    def waiting_index(self) -> int:
        """Returns the chronological place this registration has in waiting registrations.
        -1 if not waiting. Starts at 0."""
        return self._index_in_list(
            [
                r
                for r in self.event.registrations
                if r.status == RegistrationStatus.Waiting
            ]
        )

    def is_duplicate(self) -> bool:
        """Check if this registration is the duplicate of another one
        (an earlier registration exists for the same user)
        """
        return any(
            r.id < self.id
            for r in self.event.registrations
            if r.user_id == self.user_id
        )

    def is_overbooked(self) -> bool:
        """Check if the registration is overbooking.

        An overbooked registration is:

        - | an online registration with more previous Waiting registration
          | than online slots
        - | or an holding place registration with more previous holding place registration
          | than total slots
        - | a Waiting registration with more previous Waiting registration
          | than Waiting slots

        """

        return (
            self.waiting_index() >= self.event.num_waiting_list
            or self.holding_index() >= self.event.num_slots
            or self.online_index() >= self.event.num_online_slots
        )

    def is_in_late_unregistration_period(self) -> bool:
        """
        :returns: whether unregistering now should be considered "late"
        """
        if not self.event.event_type.requires_activity or not self.is_holding_slot():
            return False

        late_period_start = self.event.start - timedelta(
            hours=Configuration.LATE_UNREGISTRATION_THRESHOLD
        )
        grace_period_end = self.registration_time + timedelta(
            hours=Configuration.UNREGISTRATION_GRACE_PERIOD
        )

        return current_time() > max(late_period_start, grace_period_end)
