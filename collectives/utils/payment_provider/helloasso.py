"""Module to handle connexions to HelloAsso.

See https://dev.helloasso.com/docs for the API reference.

.. warning::
    The response payload shape used by
    :py:meth:`HelloAssoApi.retrieve_remote_payment_status` has been verified
    against a real HelloAsso checkout-intent response: the payment state is
    at ``order.payments[0].state``, not at the response root. The payload
    shape returned by :py:meth:`HelloAssoApi.do_refund` is still unverified;
    adjust it once a real refund can be tested.
"""

import json
import time
import uuid
from decimal import Decimal
from typing import Optional

import requests
from flask import current_app, request, url_for

from collectives.models import Configuration, User
from collectives.models.payment import Payment, PaymentStatus, PaymentType
from collectives.utils.payment_provider import (
    CheckoutResult,
    PaymentProvider,
    PaymentStatusResult,
    RefundResult,
    register_provider,
    unique_order_ref,
)

PROD_API_BASE = "https://api.helloasso.com"
""" Base URL for the production HelloAsso API"""

SANDBOX_API_BASE = "https://api.helloasso-sandbox.com"
""" Base URL for the HelloAsso sandbox/test API"""

API_VERSION = "v5"
""" HelloAsso API version used for all REST calls"""

REQUEST_TIMEOUT = 10
""" Timeout in seconds for calls to the HelloAsso API"""


def _log_api_error(err: requests.RequestException):
    """Logs a HelloAsso API error, including the response body when available
    (e.g. HelloAsso's detail of why a 400 Bad Request was rejected), which
    plain ``str(err)`` does not include.

    :param err: The exception raised by the failed request
    """
    body = None
    if err.response is not None:
        try:
            body = err.response.text
        except Exception:  # pylint: disable=broad-except
            body = None
    current_app.logger.error(f"HelloAsso API error: {err} - Response body: {body}")


def _map_status(state: str) -> PaymentStatus:
    """Maps a HelloAsso payment state to our generic
    :py:class:`collectives.models.payment.PaymentStatus` enum.

    :param state: The `state` field of a HelloAsso payment
        (``order.payments[0].state`` in a checkout-intent response), using
        HelloAsso's ``PaymentState`` enum, per
        https://dev.helloasso.com/reference/get_organizations-organizationslug-checkout-intents-checkoutintentid
    :return: The corresponding payment status
    """
    mapping = {
        # In progress, no final result yet
        "Pending": PaymentStatus.Initiated,
        "Waiting": PaymentStatus.Initiated,
        "WaitingBankValidation": PaymentStatus.Initiated,
        "WaitingBankWithdraw": PaymentStatus.Initiated,
        "WaitingAuthentication": PaymentStatus.Initiated,
        "Init": PaymentStatus.Initiated,
        # Successful
        "Authorized": PaymentStatus.Approved,
        "AuthorizedPreprod": PaymentStatus.Approved,
        "Registered": PaymentStatus.Approved,
        "Corrected": PaymentStatus.Approved,
        # Failed
        "Refused": PaymentStatus.Refused,
        "Unknown": PaymentStatus.Refused,
        "Error": PaymentStatus.Refused,
        "Abandoned": PaymentStatus.Refused,
        "Deleted": PaymentStatus.Refused,
        "Inconsistent": PaymentStatus.Refused,
        "NoDonation": PaymentStatus.Refused,
        "Contested": PaymentStatus.Refused,
        # Refunded
        "Refunded": PaymentStatus.Refunded,
        "Refunding": PaymentStatus.Refunded,
        # Cancelled (HelloAsso uses the single-l American spelling)
        "Canceled": PaymentStatus.Cancelled,
    }
    return mapping.get(state, PaymentStatus.Initiated)


class HelloAssoApi(PaymentProvider):
    """REST client to process payments with HelloAsso"""

    payment_type = PaymentType.HelloAsso

    def __init__(self):
        """Constructor"""

        self.client_id: str = ""
        """ HelloAsso API client id"""
        self.client_secret: str = ""
        """ HelloAsso API client secret"""
        self.organization_slug: str = ""
        """ Slug of the HelloAsso organization used to receive payments"""
        self.sandbox: bool = True
        """ Whether to use the HelloAsso sandbox/test environment"""

        self._access_token: str = ""
        """ Cached OAuth2 access token"""
        self._token_expiry: float = 0.0
        """ Monotonic timestamp at which :py:attr:`_access_token` expires"""

    def reload_config(self):
        """Reads current configuration"""

        organization_changed = (
            self.organization_slug != Configuration.HELLOASSO_ORGANIZATION_SLUG
        )

        self.client_id = Configuration.HELLOASSO_CLIENT_ID
        self.client_secret = Configuration.HELLOASSO_CLIENT_SECRET
        self.organization_slug = Configuration.HELLOASSO_ORGANIZATION_SLUG
        self.sandbox = Configuration.HELLOASSO_SANDBOX

        if organization_changed:
            self._access_token = ""
            self._token_expiry = 0.0
            if self.disabled():
                current_app.logger.warning(
                    "HelloAsso payment API disabled, using mock API"
                )

    def disabled(self) -> bool:
        """Check if a HelloAsso client id has been set.
        :return: True if HelloAssoApi is disabled.
        """
        return not self.client_id

    @property
    def _api_base(self) -> str:
        """:return: The base API URL for the configured environment (sandbox or prod)"""
        return SANDBOX_API_BASE if self.sandbox else PROD_API_BASE

    def _access_token_value(self) -> str:
        """Returns a valid OAuth2 access token, fetching/refreshing it if needed.

        :return: A bearer access token
        """
        if self._access_token and time.monotonic() < self._token_expiry:
            return self._access_token

        response = requests.post(
            f"{self._api_base}/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()

        self._access_token = payload["access_token"]
        # Refresh a bit ahead of actual expiry to avoid races
        self._token_expiry = time.monotonic() + payload.get("expires_in", 1800) - 30

        return self._access_token

    def _headers(self) -> dict:
        """:return: HTTP headers to authenticate a request to the HelloAsso API"""
        return {"Authorization": f"Bearer {self._access_token_value()}"}

    def create_checkout(self, payment: Payment, user: User) -> Optional[CheckoutResult]:
        """See :py:meth:`collectives.utils.payment_provider.PaymentProvider.create_checkout`"""
        self.reload_config()

        # Token we mint ourselves: HelloAsso's own checkout intent id is only
        # known after creation, but the return/back/error URLs must be set
        # at creation time, so we embed our own token in them upfront.
        token = str(uuid.uuid4())

        if self.disabled():
            # Dev mode, every payment is valid with fake token
            return CheckoutResult(
                accepted=True,
                token=token,
                redirect_url=url_for("payment.do_mock_payment", token=token),
            )

        amount_in_cents = int((payment.amount_charged * 100).to_integral_exact())
        item_name = (
            f"{payment.item.event.title} -- {payment.item.title} -- "
            f"{payment.price.title}"
        )[:250]

        email = user.mail if "@" in user.mail else f"{user.mail}@example.com"

        payload = {
            "totalAmount": amount_in_cents,
            "initialAmount": amount_in_cents,
            "itemName": item_name,
            # HelloAsso rejects http:// redirect URLs as invalid, even for
            # localhost - force https regardless of how this Flask app is
            # actually being served locally.
            "backUrl": url_for(
                "payment.cancel", _external=True, _scheme="https", token=token
            ),
            "errorUrl": url_for(
                "payment.cancel", _external=True, _scheme="https", token=token
            ),
            "returnUrl": url_for(
                "payment.process", _external=True, _scheme="https", token=token
            ),
            "containsDonation": False,
            "payer": {
                "firstName": user.first_name,
                "lastName": user.last_name,
                "email": email,
            },
            "metadata": {
                "collective_id": str(payment.item.event.id),
                "payment_ref": unique_order_ref(payment),
            },
        }

        try:
            response = requests.post(
                f"{self._api_base}/{API_VERSION}/organizations/"
                f"{self.organization_slug}/checkout-intents",
                json=payload,
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as err:
            _log_api_error(err)
            return None

        data = response.json()

        return CheckoutResult(
            accepted=True,
            token=token,
            redirect_url=data["redirectUrl"],
            raw_metadata=json.dumps(data),
        )

    def retrieve_remote_payment_status(
        self, payment: Payment
    ) -> Optional[PaymentStatusResult]:
        """See :py:meth:`collectives.utils.payment_provider.PaymentProvider.retrieve_remote_payment_status`"""
        self.reload_config()

        if self.disabled():
            # Dev mode, result is read from url parameters
            message = request.args.get("message")
            amount = request.args.get("amount") or "0"
            status = {
                "ACCEPTED": PaymentStatus.Approved,
                "REFUSED": PaymentStatus.Refused,
                "CANCELLED": PaymentStatus.Cancelled,
            }.get(message, PaymentStatus.Initiated)
            response = {"state": message, "order": {"amount": {"total": amount}}}
            return PaymentStatusResult(
                status=status,
                amount=Decimal(amount) / 100,
                raw_metadata=json.dumps(response),
            )

        checkout_intent_id = self._checkout_intent_id(payment)
        if checkout_intent_id is None:
            current_app.logger.error(
                f"HelloAsso: missing checkout intent id for payment {payment.id}"
            )
            return None

        try:
            response = requests.get(
                f"{self._api_base}/{API_VERSION}/organizations/"
                f"{self.organization_slug}/checkout-intents/{checkout_intent_id}",
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as err:
            _log_api_error(err)
            return None

        data = response.json()
        order = data.get("order") or {}
        amount_in_cents = (order.get("amount") or {}).get("total", 0)
        payments = order.get("payments") or []
        state = payments[0].get("state", "") if payments else ""

        return PaymentStatusResult(
            status=_map_status(state),
            amount=Decimal(amount_in_cents) / 100,
            raw_metadata=json.dumps(data),
        )

    def do_refund(self, payment: Payment) -> Optional[RefundResult]:
        """See :py:meth:`collectives.utils.payment_provider.PaymentProvider.do_refund`"""
        self.reload_config()

        if self.disabled():
            # Dev mode, refund always succeeds
            return RefundResult(
                accepted=True, raw_metadata=json.dumps({"state": "Refunded"})
            )

        payment_id = self._helloasso_payment_id(payment)
        if payment_id is None:
            current_app.logger.error(
                f"HelloAsso: missing payment id for refund of payment {payment.id}"
            )
            return None

        try:
            response = requests.post(
                f"{self._api_base}/{API_VERSION}/payments/{payment_id}/refund",
                json={"cancelOrder": False},
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as err:
            _log_api_error(err)
            return None

        return RefundResult(accepted=True, raw_metadata=json.dumps(response.json()))

    @staticmethod
    def _checkout_intent_id(payment: Payment) -> Optional[str]:
        """Extracts the HelloAsso checkout intent id stored on a payment's
        raw metadata (saved there right after :py:meth:`create_checkout`).

        :param payment: The database payment entry
        :return: The checkout intent id, or None if not found
        """
        try:
            return json.loads(payment.raw_metadata or "{}").get("id")
        except (json.JSONDecodeError, AttributeError):
            return None

    @staticmethod
    def _helloasso_payment_id(payment: Payment) -> Optional[str]:
        """Extracts the HelloAsso payment id (within the order tied to this
        checkout intent) from the payment's raw metadata, as last fetched by
        :py:meth:`retrieve_remote_payment_status`.

        :param payment: The database payment entry
        :return: The HelloAsso payment id, or None if not found
        """
        try:
            metadata = json.loads(payment.raw_metadata or "{}")
            payments = ((metadata.get("order") or {}).get("payments")) or []
            return payments[0]["id"] if payments else None
        except (json.JSONDecodeError, AttributeError, KeyError, IndexError):
            return None


api: HelloAssoApi = HelloAssoApi()
""" HelloAssoApi object that will handle requests to HelloAsso.

`api` requires to be initialized with :py:meth:`HelloAssoApi.init_app` to be used.
"""

register_provider(api)
