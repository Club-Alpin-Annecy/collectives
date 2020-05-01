"""Module defining payment-related models
"""

from .globals import db
from .utils import ChoiceEnum


class PaymentOption(db.Model):
    """ Database model describing a payment option for a given event
        E.g. 'Pass', 'Pass + transport', ...

        :todo: Add constraint on license type
        :todo: Add constraint on date range
    """

    __tablename__ = "payment_options"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    event_id = db.Column(
        db.Integer, db.ForeignKey("events.id"), index=True, nullable=False
    )
    """ Primary key of the event to which this payment option is associated

    :type: int"""

    title = db.Column(db.String(256), nullable=False)
    """ Display title for this payment option

    :type: string"""

    price_in_cents = db.Column(db.Integer, nullable=False)
    """ Price in euro cents

    :type: int"""

    # Relationships

    payments = db.relationship("Payment", backref="payment_option", lazy=True)
    """ List of payments associated to this payment option.

    :type: list(:py:class:`collectives.models.payment.Payment`)
    """


class PaymentType(ChoiceEnum):
    """ Enum describing the type of payment
    """

    Online = 0
    """ Payment has been made through the online payment processor
    """
    Check = 1
    """ Payment has been made by check
    """
    Cash = 2
    """ Payment has been made by cash
    """


class PaymentStatus(ChoiceEnum):
    """ Enum describing the current state of the payment at a high level
    """

    Initiated = 0
    """ Payment has been initiated, waiting for a response from the processor
    """
    Approved = 1
    """ Payment has been approved
    """
    Cancelled = 2
    """ Payment has been cancelled by the user
    """
    Refused = 3
    """ Payment has been refused by the processor
    """
    Expired = 4
    """ Payment has expired due to timeout
    """


class Payment(db.Model):

    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    registration_id = db.Column(
        db.Integer, db.ForeignKey("registrations.id"), index=True
    )
    """ Primary key of the registration this payment is associated to

    :type: int"""

    payment_option_id = db.Column(
        db.Integer, db.ForeignKey("payment_options.id"), nullable=False
    )
    """ Primary key of the payment option this payment is associated to

    :type: int"""

    creditor_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), index=True, nullable=False
    )
    """ Primary key of the user making this payment
    Should be similar to registration.user_id, but copied here in case registration is deleted

    :type: int"""

    reporter_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), index=True, nullable=False
    )
    """ Primary key of the user reporting this payment
    For online payments this should be similar to creditor_id, for manual payments this
    would be the id of the leader/admin who reported the payment

    :type: int"""

    payment_type = db.Column(db.Enum(PaymentType), nullable=False)
    """ Payment type (online, cash, ...)

    :type: :py:class:`collectives.models.payment.PaymentType`"""

    status = db.Column(db.Enum(PaymentStatus), nullable=False)
    """ Current status of the payment

    :type: :py:class:`collectives.models.payment.PaymentStatus`"""

    creation_time = db.Column(db.DateTime, nullable=False)
    """ Timestamp at which the payment was created

    :type: :py:class:`datetime.datetime`"""

    finalization_time = db.Column(db.DateTime)
    """ Timestamp at which the payment was finalized (approved/cancelled)

    :type: :py:class:`datetime.datetime`"""

    processor_token = db.Column(db.String(256), index=True, nullable=False)
    """ Unique identifier of this payment for the payment processor.
        To be refined.

    :type: str
    """

    raw_metadata = db.Column(db.Text, nullable=False)
    """ Raw metadata concerning this payment as returned by the payment processor,
        or paymentr details if it had been made by cash/check
        To be refined.

    :type: str
    """

    amount_charged_in_cents = db.Column(db.Integer, nullable=False)
    """ Amount in euro cents to be paid by the user. Stored locally as the
    payment option price might have been updated.

    :type: int"""

    amount_paid_in_cents = db.Column(db.Integer, nullable=False)
    """ Amount in euro cents paid by the user if the payment has been approved.
    For validation purposes

    :type: int"""
