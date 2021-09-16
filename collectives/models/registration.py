"""Module for registration related classes
"""
import enum
from .globals import db
from .utils import ChoiceEnum


class RegistrationLevels(enum.IntEnum):
    """Enum listing acceptable registration levels.

    A registration level is type of event participant, such as a co-leader or a regular participant."""

    Normal = 0
    """ Normal participant, no specific power. """

    CoLeader = 1
    """ Participant that will help the event leader."""


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
    Unsubscribed = 3
    """ User has self unsubscribed to the event.

    User should not be able to register again without leader help."""

    Present = 4
    """ User has been present to the event."""

    ExcusedAbsentee = 5
    """ User has been absent to the event, but excused by the leader. """

    NotExcusedAbsentee = 6
    """ User has been absent to the event, but not excused by the leader. """

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
            cls.Unsubscribed: "Désinscrit",
            cls.Present: "Présent",
            cls.ExcusedAbsentee: "Absent Excusé",
            cls.NotExcusedAbsentee: "No show",
        }


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
    """ Primary key of the event to which the user is registered (see  :py:class:`collectives.models.event.Event`)

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

    # Relationships

    payments = db.relationship("Payment", backref="registration", lazy=True)
    """ List of payments associated to this registration.

    :type: list(:py:class:`collectives.models.payment.Payment`)
    """

    def is_active(self):
        """Check if this registation is active.

        :return: True if :py:attr:`status` is `Active` and the user's license has not expired
        :rtype: boolean"""
        return (
            self.status == RegistrationStatus.Active and not self.is_pending_renewal()
        )

    def is_planned(self):
        """Check if this registation is not rejected or unsubscribed

        :return: True if :py:attr:`status` is `Present`, `ExcusedAbsentee`, `NotExcusedAbsentee`, `Active`
        :rtype: boolean"""
        return self.status in [
            RegistrationStatus.Present,
            RegistrationStatus.ExcusedAbsentee,
            RegistrationStatus.NotExcusedAbsentee,
            RegistrationStatus.Active,
        ]

    def is_valid(self):
        """Check if this registation is present or active

        :return: True if :py:attr:`status` is `Present` or `Active`
        :rtype: boolean"""
        return self.status in [RegistrationStatus.Present, RegistrationStatus.Active]

    def is_holding_slot(self):
        """Check if this registation is holding a slot.

        :return: Is :py:attr:`status` planned or pending?
        :rtype: boolean"""
        return self.is_planned() or self.status == RegistrationStatus.PaymentPending

    def is_rejected(self):
        """Check if this registation is rejected.

        :return: Is :py:attr:`status` rejected ?
        :rtype: boolean"""
        return self.status == RegistrationStatus.Rejected

    def is_unsubscribed(self):
        """Check if this registation is unsubscribed.

        :return: Is :py:attr:`status` unsubscribed ?
        :rtype: boolean"""
        return self.status == RegistrationStatus.Unsubscribed

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
