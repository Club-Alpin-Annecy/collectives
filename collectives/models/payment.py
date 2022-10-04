"""Module defining payment-related models
"""

from decimal import Decimal
from datetime import timedelta

from wtforms.validators import NumberRange

from collectives.models.event import Event
from collectives.models.globals import db
from collectives.models.utils import ChoiceEnum
from collectives.models.registration import RegistrationStatus
from collectives.utils.time import current_time


class PaymentItem(db.Model):
    """Database model describing a paid item for a given event
    E.g. 'Pass', 'Pass + transport', ...
    """

    __tablename__ = "payment_items"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    event_id = db.Column(
        db.Integer, db.ForeignKey("events.id"), index=True, nullable=False
    )
    """ Primary key of the event to which this payment option is associated

    :type: int"""

    title = db.Column(
        db.String(256), nullable=False, info={"label": "Objet du paiement"}
    )
    """ Display title for this payment option

    :type: string"""

    # Relationships

    prices = db.relationship(
        "ItemPrice", backref="item", lazy=True, cascade="all, delete-orphan"
    )
    """ List of prices associated to this payment item.

    :type: list(:py:class:`collectives.models.payment.ItemPrice`)
    """

    payments = db.relationship("Payment", backref="item", lazy=True)
    """ List of payments associated to this payment item.

    :type: list(:py:class:`collectives.models.payment.Payment`)
    """

    def copy(self, time_shift=timedelta(0)):
        """Copy current payment item.

        Copy also price but not payments.

        :param time_shift: Optionnal shift of copied item prices dates
        :type time_shift: :py:class:`datetime.timedelta`
        :returns: Copied :py:class:`collectives.models.payments.PaymentItem`"""
        item = PaymentItem()
        item.title = self.title
        for price in self.prices:
            item.prices.append(price.copy(time_shift))
        return item

    def active_prices(self):
        """
        :return: All active prices associated to this item
        :rtype: list[:py:class:`collectives.models.payment.ItemPrice`]
        """
        return [p for p in self.prices if p.enabled]

    def available_prices_to_user(self, user):
        """Returns all prices that are available to a given user
        at any point in time

        :param user:  The candidate user
        :type user: :py:class:`collectives.models.user.User`

        :return: List of available prices
        :rtype: list[:py:class:`collectives.models.payment.ItemPrice`]
        """
        return [
            p
            for p in self.active_prices()
            if p.is_available_to_user(user) and p.has_available_use()
        ]

    def available_prices_to_user_at_date(self, user, date):
        """Returns all prices that are available to a given user
        at a given date

        :param user:  The candidate user
        :type user: :py:class:`collectives.models.user.User`
        :param date:  The considered date
        :type date: :py:class:`datetime.date`
        :return: List of available prices
        :rtype: list[:py:class:`collectives.models.payment.ItemPrice`]
        """
        return [
            p
            for p in self.available_prices_to_user(user)
            if p.is_available_at_date(date)
        ]

    def cheapest_price_for_user_at_date(self, user, date):
        """Returns the cheapest price available to a given user
        at a given date

        :param user:  The candidate user
        :type user: :py:class:`collectives.models.user.User`
        :param date:  The considered date
        :type date: :py:class:`datetime.date`
        :return: List of available prices
        :rtype: list[:py:class:`collectives.models.payment.ItemPrice`]
        """
        available_prices = self.available_prices_to_user_at_date(user, date)
        if len(available_prices) == 0:
            return None
        return min(available_prices, key=lambda p: p.amount)

    def cheapest_price_for_user_now(self, user):
        """Returns the cheapest price available to a given user
        at the current time

        :param user:  The candidate user
        :type user: :py:class:`collectives.models.user.User`

        :return: List of available prices
        :rtype: list[:py:class:`collectives.models.payment.ItemPrice`]
        """
        current_date = current_time().date()
        return self.cheapest_price_for_user_at_date(user, current_date)


class ItemPrice(db.Model):
    """Database model describing prices for a payment item
    E.g. 'Youth ', 'Early bird', ...

    :todo: Add constraint on license type
    :todo: Add constraint on date range
    """

    __tablename__ = "item_prices"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    item_id = db.Column(
        db.Integer, db.ForeignKey("payment_items.id"), index=True, nullable=False
    )
    """ Primary key of the item to which this price is associated

    :type: int"""

    title = db.Column(
        db.String(256), nullable=False, info={"label": "Intitulé du tarif"}
    )
    """ Subtitle for this price

    :type: string"""

    license_types = db.Column(db.String(256), info={"label": "Catégories de licence"})
    """ List of comma-separated license-types to which this price applies.
    If the list is NULL or left empty, then the price applies to all licence types

    :type: string"""

    start_date = db.Column(db.Date(), info={"label": "Date de début"})
    """ Date at which this price will start to be available

    :type: :py:class:`datetime.date`"""

    end_date = db.Column(db.Date(), info={"label": "Date de fin"})
    """ Date at which this price will stop to be available

    :type: :py:class:`datetime.date`"""

    amount = db.Column(db.Numeric(precision=8, scale=2), nullable=False)
    """ Charged amount in euros

    :type: :py:class:`decimal.Decimal`"""

    max_uses = db.Column(
        db.Integer, info={"label": "Max dispo", "validators": NumberRange(0)}
    )
    """ Max number of times this price can be used.
    If the number is NULL, then the number of times is unlimited

    :type: string"""

    enabled = db.Column(
        db.Boolean, nullable=False, default=False, info={"label": "Activer le tarif"}
    )
    """ Whether this price is enabled.
    Ideally, prices should be disabled rather than fully deleted
    once at least one person has used the

    :type: bool"""

    leader_only = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        info={"label": "Tarif encadrant"},
    )
    """ Whether this price is only available to the event leaders.

    :type: bool"""

    update_time = db.Column(db.DateTime, nullable=False)
    """ Time at which the price was last updated

    :type: :py:class:`datetime.datetime`"""

    parent_event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        info={"label": "Evènement parent"},
    )
    """ Parent event id, where user is required to have subscribed to get the price."""

    # Relationships

    payments = db.relationship("Payment", backref="price", lazy=True)
    """ List of payments associated to this payment option.

    :type: list(:py:class:`collectives.models.payment.Payment`)
    """

    parent_event = db.relationship(
        "Event", backref="children_payments", remote_side=[Event.id], lazy=True
    )
    """ User has to have subscribed to this event to get this price.

    :type: list(:py:class:`collectives.models.event.Event`)
    """

    def copy(self, time_shift=timedelta(0)):
        """Copy this price.

        :type time_shift: :py:class:`datetime.timedelta`
        :returns: Copied :py:class:`collectives.models.payments.PaymentItem`
        :returns: Copied :py:class:`collectives.models.payments.ItemPrice`"""
        attributes = dict(self.__dict__)
        attributes.pop("id")  # get rid of id
        attributes.pop("item_id")  # get rid of item_id
        attributes.pop("_sa_instance_state")  # get rid of SQLAlchemy special attr
        copy = self.__class__(**attributes)

        if copy.start_date is not None:
            copy.start_date = copy.start_date + time_shift
        if self.end_date is not None:
            copy.end_date = copy.end_date + time_shift

        return copy

    def total_use_count(self):
        """
        Total number of times this price has been used,
        even if the corresponding registration is no longer active

        :return: total number of payments associated with this price
        :rtype: int
        """
        return len(self.payments)

    def active_use_count(self):
        """
        Number of currently active or payment pending registrations
        (i.e, registrations holding a slot or event leaders) that are using
        this price

        :return: number of payments associated with this price and an active registration
        :rtype: int
        """
        return sum(
            1
            for p in self.payments
            if (
                (p.is_approved() or p.is_unsettled())
                and (
                    (p.registration and p.registration.is_holding_slot())
                    or self.item.event.is_leader(p.buyer)
                )
            )
        )

    def has_available_use(self):
        """Returns whether there are remaining uses for this price
        :return: True if max_uses is 0 or larger than :py:meth:`active_use_count()`
        :rtype: bool
        """
        if not self.max_uses:
            return True
        return self.max_uses > self.active_use_count()

    def is_available_at_date(self, date):
        """Returns whether this price is available at a given time

        :param date:  The date at which to do the check
        :type date: :py:class:`datetime.Date`

        :return: True if the date is between start and end date or those dates are not defined
        :rtype: bool
        """
        if not self.enabled:
            return False
        if self.start_date and self.start_date > date:
            return False
        if self.end_date and self.end_date < date:
            return False
        return True

    def is_available_to_user(self, user):
        """Returns whether this price is available to an user
        at any point in time

        :param user:  The candidate user
        :type user: :py:class:`collectives.models.user.User`

        :return: True if the user license belongs to the license
                 types string (or no license types are provided)
        :rtype: bool
        """
        if not self.enabled:
            return False
        if self.leader_only and not self.item.event.is_leader(user):
            return False
        if self.parent_event is not None:
            if not self.parent_event.is_registered_with_status(
                user, [RegistrationStatus.Active]
            ):
                return False
        if not self.license_types:
            return True
        license_types = self.license_types.split()
        return len(license_types) == 0 or user.license_category in license_types


class PaymentType(ChoiceEnum):
    """Enum describing the type of payment"""

    # pylint: disable=invalid-name
    Online = 0
    """ Payment has been made through the online payment processor
    """
    Check = 1
    """ Payment has been made by check
    """
    Cash = 2
    """ Payment has been made by cash
    """
    Card = 3
    """ Payment has been using a debit or credi card
    """
    Transfer = 4
    """ Payment has been using a bank transfer
    """
    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls):
        """
        :return: a dict defining display names for all enum values
        :rtype: dict
        """
        return {
            cls.Online: "En ligne",
            cls.Check: "Chèque",
            cls.Cash: "Espèces",
            cls.Card: "CB",
            cls.Transfer: "Virement",
        }


class PaymentStatus(ChoiceEnum):
    """Enum describing the current state of the payment at a high level"""

    # pylint: disable=invalid-name
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
    Refunded = 5
    """ Payment has been refunded to the user
    """
    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls):
        """
        :return: a dict defining display names for all enum values
        :rtype: dict
        """
        return {
            cls.Initiated: "En cours",
            cls.Approved: "Approuvé",
            cls.Cancelled: "Annulé",
            cls.Refused: "Refusé",
            cls.Expired: "Inabouti",
            cls.Refunded: "Remboursé",
        }


# pylint: disable=too-many-instance-attributes
class Payment(db.Model):
    """Datable model describing the details of a payment"""

    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    registration_id = db.Column(
        db.Integer, db.ForeignKey("registrations.id"), index=True
    )
    """ Primary key of the registration this payment is associated to

    :type: int"""

    item_price_id = db.Column(
        db.Integer, db.ForeignKey("item_prices.id"), nullable=False
    )
    """ Primary key of the item price this payment is associated to

    :type: int"""

    payment_item_id = db.Column(
        db.Integer, db.ForeignKey("payment_items.id"), index=True, nullable=False
    )
    """ Primary key of the item this payment is associated to.
    Should be similar to  item_price.payment_item_id, but makes it easier
    to list all payments for a given item.

    :type: int"""

    buyer_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), index=True, nullable=False
    )
    """ Primary key of the user making this payment
    Should be similar to registration.user_id, but copied here in case registration is deleted

    :type: int"""

    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    """ Primary key of the user reporting this payment
    For online payments this should be similar to buyer, for manual payments this
    would be the id of the leader/admin who reported the payment

    :type: int"""

    payment_type = db.Column(
        db.Enum(PaymentType),
        nullable=False,
        info={
            "choices": PaymentType.choices(),
            "coerce": PaymentType.coerce,
            "label": "Moyen de paiement",
        },
    )
    """ Payment type (online, cash, ...)

    :type: :py:class:`collectives.models.payment.PaymentType`"""

    status = db.Column(
        db.Enum(PaymentStatus),
        nullable=False,
        info={
            "choices": PaymentStatus.choices(),
            "coerce": PaymentStatus.coerce,
            "label": "État du paiement",
        },
    )
    """ Current status of the payment

    :type: :py:class:`collectives.models.payment.PaymentStatus`"""

    creation_time = db.Column(db.DateTime, nullable=False)
    """ Timestamp at which the payment was created

    :type: :py:class:`datetime.datetime`"""

    finalization_time = db.Column(db.DateTime)
    """ Timestamp at which the payment was finalized (approved/cancelled)

    :type: :py:class:`datetime.datetime`"""

    refund_time = db.Column(db.DateTime)
    """ Timestamp at which the payment was refunded

    :type: :py:class:`datetime.datetime`"""

    processor_token = db.Column(db.String(256), index=True, nullable=False)
    """ Unique identifier of this payment for the payment processor.

    :type: str
    """

    processor_order_ref = db.Column(db.String(32))
    """ Human-readable order identifier for the payment processor.

    :type: str
    """

    processor_url = db.Column(db.String(255))
    """ Url that the buyer should be redirected to to make the payment

    :type: str
    """

    raw_metadata = db.Column(
        db.Text,
        nullable=False,
        info={"label": "Précisions", "description": "Par ex. numéro de chèque"},
    )
    """ Raw metadata concerning this payment as returned by the payment processor,
        or payment details if it had been made by cash/check
        To be refined.

    :type: str
    """

    refund_metadata = db.Column(db.Text)
    """ Raw metadata concerning this payment refund transaction.

    :type: str
    """

    amount_charged = db.Column(db.Numeric(precision=8, scale=2), nullable=False)
    """ Amount in euros to be paid by the user. Stored locally as the
    payment item price might have been updated while the payment is
    being processed.

    :type: :py:class:`decimal.Decimal`"""

    amount_paid = db.Column(
        db.Numeric(precision=8, scale=2), nullable=False, info={"label": "Prix payé"}
    )
    """ Amount in euros paid by the user if the payment has been approved.
    For validation purposes

    :type: :py:class:`decimal.Decimal`"""

    terms_version = db.Column(db.String(255), nullable=True)
    """ Version of the payment terms and condition at the time of payment

    :type: string"""

    def is_offline(self):
        """:return: whether this is an offline payment (Check, Card, etc)
        :rtype: bool"""
        return self.payment_type != PaymentType.Online

    def is_unsettled(self):
        """:return: whether this payment is not finalized yet. Applies mostly to Online payments
        :rtype: bool"""
        return self.status == PaymentStatus.Initiated

    def is_approved(self):
        """:return: whether this payment has been accepted
        :rtype: bool"""
        return self.status == PaymentStatus.Approved

    def has_receipt(self):
        """:return: whether this payment has an associated receipt
                    (i.e. if it is an approved online payment)
        :rtype: bool"""
        return self.payment_type == PaymentType.Online and self.is_approved()

    def has_refund_receipt(self):
        """:return: whether this payment has an associated refund receipt
                    (i.e. if it is a refunded online payment)
        :rtype: bool"""
        return (
            self.payment_type == PaymentType.Online
            and self.status == PaymentStatus.Refunded
        )

    def __init__(self, registration=None, item_price=None, buyer=None):
        """Overloaded constructor.
        Pre-fill a Payment object from an existing registration and item price
        """

        super().__init__()

        if registration is not None:
            self.registration_id = registration.id
            if buyer is None:
                buyer = registration.user

        if buyer is not None:
            self.buyer_id = buyer.id
            self.reporter_id = buyer.id

        if item_price is not None:
            self.item_price_id = item_price.id
            self.payment_item_id = item_price.item.id
            self.amount_charged = item_price.amount
            self.amount_paid = Decimal(0)
            self.payment_type = PaymentType.Online
            self.status = PaymentStatus.Initiated
            self.processor_token = ""
            self.raw_metadata = ""
            self.creation_time = current_time()
