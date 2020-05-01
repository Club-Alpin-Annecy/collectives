"""Module for registration related classes
"""
import enum
from .globals import db


class RegistrationLevels(enum.IntEnum):
    """ Enum listing acceptable registration levels.

    A registration level is type of event participant, such as a co-leader or a regular participant. """

    Normal = 0
    """ Normal participant, no specific power. """

    CoLeader = 1
    """ Participant that will help the event leader."""


class RegistrationStatus(enum.IntEnum):
    """ Enum listing acceptable registration status. """

    Active = 0
    """ Registered user is plann to be present. """

    Rejected = 1
    """ Registered user has been rejected by a leader.

    A rejected user shall not be counted in occupied slots, nor be able to register again"""
    PaymentPending = 2
    """ User has initiated but not yet completed payment

    This registration is temporarily holding up a spot, but may be removed after timeout
    """


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

    # Relationships

    payments = db.relationship("Payment", backref="registration", lazy=True)
    """ List of payments associated to this registration.

    :type: list(:py:class:`collectives.models.payment.Payment`)
    """

    def is_active(self):
        """Check if this registation is active.

        :return: Is :py:attr:`status` active ?
        :rtype: boolean"""
        return self.status == RegistrationStatus.Active

    def is_holding_slot(self):
        """Check if this registation is holding a slot.

        :return: Is :py:attr:`status` active or pending?
        :rtype: boolean"""
        return (
            self.status == RegistrationStatus.Active
            or self.status == RegistrationStatus.PaymentPending
        )

    def is_rejected(self):
        """Check if this registation is rejected.

        :return: Is :py:attr:`status` rejected ?
        :rtype: boolean"""
        return self.status == RegistrationStatus.Rejected
