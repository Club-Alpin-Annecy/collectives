"""Abstraction over online payment processors (Payline, HelloAsso, ...).

Routes and other call sites should go through :py:func:`get_active_provider`
or :py:func:`get_provider_by_name` rather than importing a specific processor
module directly, so that the payment processor used by the site can be
selected through the admin configuration (``Configuration.PAYMENT_ENABLED``).
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

from collectives.models import Configuration, User
from collectives.models.payment import Payment, PaymentStatus, PaymentType


@dataclass
class CheckoutResult:
    """Result of a checkout creation request."""

    accepted: bool
    """Whether the checkout was successfully created."""
    token: str = ""
    """Processor token identifying the checkout, to be stored as
    :py:attr:`collectives.models.payment.Payment.processor_token`."""
    redirect_url: str = ""
    """URL the buyer's browser should be redirected to to complete payment."""
    raw_metadata: str = ""
    """Optional JSON-encoded raw response from the processor's checkout
    creation call, to be stored immediately as
    :py:attr:`collectives.models.payment.Payment.raw_metadata` so that
    later status/refund lookups can recover processor-specific identifiers
    (e.g. HelloAsso's checkout intent id). Left empty when the processor's
    own token is sufficient on its own, as with Payline."""
    error_code: str = ""
    error_message: str = ""


@dataclass
class PaymentStatusResult:
    """Result of a payment status query."""

    status: PaymentStatus
    amount: Decimal
    raw_metadata: str
    """JSON-encoded raw response from the processor, to be stored as
    :py:attr:`collectives.models.payment.Payment.raw_metadata`."""


@dataclass
class RefundResult:
    """Result of a refund request."""

    accepted: bool
    raw_metadata: str = ""
    error_code: str = ""
    error_message: str = ""


class PaymentProvider(ABC):
    """Interface that online payment processor integrations must implement.

    A concrete implementation wraps a specific processor's API (SOAP, REST, ...)
    and exposes it through this processor-agnostic surface, so that
    :py:mod:`collectives.routes.payment` does not need to know which processor
    is active.
    """

    payment_type: PaymentType
    """Payment type identifying this provider (e.g. ``PaymentType.Payline``),
    stored on :py:attr:`collectives.models.payment.Payment.payment_type` for
    every payment it processes."""

    def reload_config(self):
        """Reads current configuration, resetting any cached client if necessary."""

    @abstractmethod
    def disabled(self) -> bool:
        """
        :return: True if this provider is not configured and should
            operate in mock mode.
        """

    @abstractmethod
    def create_checkout(self, payment: Payment, user: User) -> Optional[CheckoutResult]:
        """Initiates a hosted checkout for the given payment and buyer.

        :param payment: The database payment entry being paid for
        :param user: The user making the payment
        :return: The checkout result, or None if the API call failed outright
        """

    @abstractmethod
    def retrieve_remote_payment_status(
        self, payment: Payment
    ) -> Optional[PaymentStatusResult]:
        """Retrieves the current status of a previously initiated payment
        from the payment processor.

        :param payment: The database payment entry, as previously updated by
            :py:meth:`create_checkout` (uses ``payment.processor_token`` and,
            if needed, other processor-specific data stored on the payment)
        :return: The payment status, or None if the API call failed
        """

    @abstractmethod
    def do_refund(self, payment: Payment) -> Optional[RefundResult]:
        """Tries to refund a previously approved online payment.

        :param payment: The database payment entry to refund
        :return: The refund result, or None if the API call failed outright
        """

    def parse_callback(
        self, endpoint: str, args: Dict[str, Any], form: Dict[str, Any]
    ) -> Optional[str]:
        """Extracts the processor token from a callback/webhook request.

        Default implementation reads a `token` query or form parameter;
        override for processors using a different parameter name or payload
        shape (e.g. a JSON webhook body).

        :param endpoint: The Flask endpoint that was hit (`payment.process`,
            `payment.cancel` or `payment.notify`)
        :param args: Request query parameters
        :param form: Request form parameters
        :return: The processor token, or None if it could not be found
        """
        token = args.get("token")
        if token is None:
            token = form.get("token")
        return token

    @property
    def mock_callback_param(self) -> str:
        """:return: Name of the query parameter carrying the token on the
        mock payment page, when this provider is disabled/in mock mode."""
        return "token"


_PROVIDERS: Dict[PaymentType, PaymentProvider] = {}
"""Registry of known providers, keyed by :py:attr:`PaymentProvider.payment_type`."""


def register_provider(provider: PaymentProvider):
    """Registers a provider so it can be resolved by name.

    :param provider: The provider singleton to register
    """
    _PROVIDERS[provider.payment_type] = provider


def get_provider_by_name(name: PaymentType) -> PaymentProvider:
    """Returns the provider singleton with the given name.

    Used to process payments/refunds for a specific historical payment,
    regardless of which provider is currently configured as active.

    :param name: Provider name, e.g. ``PaymentType.Payline`` or ``PaymentType.HelloAsso``
    :return: The corresponding provider singleton
    """
    return _PROVIDERS[name]


def get_active_provider() -> PaymentProvider:
    """:return: The currently configured, active payment provider."""
    return get_provider_by_name(PaymentType[Configuration.PAYMENT_ENABLED])


def retrieve_remote_status(payment: Payment) -> Optional[PaymentStatusResult]:
    """Retrieves the current status of a payment from the processor that
    originally handled it, regardless of which provider is currently active.

    :param payment: The database payment entry to check
    :return: The payment status, or None if the API call failed
    """
    return get_provider_by_name(payment.payment_type).retrieve_remote_payment_status(
        payment
    )


def get_all_providers() -> list:
    """:return: All registered provider singletons, in registration order.

    Used to parse an incoming payment callback/webhook whose issuing
    provider is not known upfront (see
    :py:meth:`PaymentProvider.parse_callback`).
    """
    return list(_PROVIDERS.values())


def unique_order_ref(payment: Optional[Payment]) -> str:
    """Builds a unique, human-readable order reference for a payment.

    Shared across providers so that `Payment.processor_order_ref` (shown to
    users/accountants as "Référence") keeps the same format regardless of
    which processor handled the payment.

    :param payment: The payment being ordered, or None
    :return: A unique reference
    """
    if payment is None:
        return str(uuid.uuid4())

    # Date with format YYYYMMDD
    date_str = payment.creation_time.strftime("%Y%m%d")
    # Activity trigram
    if payment.item.event.activity_types:
        activity_str = payment.item.event.activity_types[0].trigram
    else:
        activity_str = "NCL"
    # Rolling id making sure we can't get the same ref for distinct orders
    rolling_id = payment.id % 10000

    return f"CAF{date_str}{activity_str}{rolling_id:04}"


# Concrete providers must be imported after the definitions above, since they
# call register_provider() at module load time; importing them here (instead
# of relying on some other module to do it) guarantees that importing this
# package is enough for get_provider_by_name()/get_active_provider() to work.
from collectives.utils.payment_provider import helloasso, payline  # noqa: E402
