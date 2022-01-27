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
    SelfUnregistered = 3
    """ User has self unregister to the event.

    User should not be able to register again without leader help."""

    JustifiedAbsentee = 4
    """ User has been absent to the event, but excused by the leader. """

    UnJustifiedAbsentee = 5
    """ User has been absent to the event, but not excused by the leader. """

    ToBeDeleted = 99999
    """ Registration should be deleted. This is not a valid SQL enum entry and should only be used as a temporary marker"""

    Waiting = 6
    """ User is in waiting list. """

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
            cls.JustifiedAbsentee: "Absent justifié",
            cls.UnJustifiedAbsentee: "Absent non justifié",
            cls.ToBeDeleted: "Effacer l'inscription",
            cls.Waiting: "Liste d'attente",
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
            ],
            cls.Rejected: [re_register_status, cls.ToBeDeleted, cls.Waiting],
            cls.PaymentPending: [cls.Rejected],
            cls.SelfUnregistered: [re_register_status, cls.Waiting, cls.ToBeDeleted],
            cls.JustifiedAbsentee: [cls.Rejected, cls.Active, cls.UnJustifiedAbsentee],
            cls.UnJustifiedAbsentee: [cls.Rejected, cls.Active, cls.JustifiedAbsentee],
            cls.ToBeDeleted: [],
            cls.Waiting: [cls.Rejected, re_register_status],
        }

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

    def is_holding_slot(self):
        """Check if this registation is holding a slot.

        :return: Is :py:attr:`status` active or pending?
        :rtype: boolean"""
        return self.status in (
            RegistrationStatus.Active,
            RegistrationStatus.PaymentPending,
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
