"""Module to handle connexions to Payline."""

import base64
import decimal
import json
import uuid
from typing import Any, Dict

import pysimplesoap
from flask import Flask, current_app, request, url_for
from pysimplesoap.client import SoapClient

from collectives.models import Configuration, User
from collectives.models.payment import Payment, PaymentStatus
from collectives.utils.misc import to_ascii, truncate
from collectives.utils.time import format_date

PAYLINE_VERSION = 26
""" Version of payline API
:type: int
"""

PAYMENT_ACTION = 101
"""
Payment action, as per https://docs.payline.com/display/DT/Codes+-+Action
101 stand for "Authorization and Capture"

:type: int
"""

PAYMENT_MODE = "CPT"
"""Payment mode, as per https://docs.payline.com/display/DT/Codes+-+Mode
CPT stands for "Full"

:type: string
"""


class PaymentResult:
    """Result returned after payline API requests. Gives information
    about whether the request has succeeded, or why it has not

    :param response: response dictionary from SOAP endpoint
    """

    def __init__(self, response: Dict[str, str] = None):
        """Constructor"""

        self.code = ""
        """ Return code, see https://docs.payline.com/display/DT/Return+codes"""
        self.short_message = ""
        """ short message of transaction status
        i.e. : ACCEPTED, REFUSED, ERROR...
        See https://docs.payline.com/display/DT/Codes+-+ShortMessage"""
        self.long_message = ""
        """ long message of transaction status details"""

        if response is not None:
            self.code = response["code"]
            self.long_message = response["longMessage"]
            self.short_message = response["shortMessage"]

    def payment_status(self) -> PaymentStatus:
        """Maps the API response short message and code to
        a value from our PaymentStatus enum.

        :return: The corresponding payment status
        """
        if self.short_message == "ACCEPTED":
            return PaymentStatus.Approved
        if self.short_message == "CANCELLED":
            return PaymentStatus.Cancelled
        if self.short_message == "REFUSED":
            if self.code == "02533":
                # If the user has not been redirected to the payment page yet,
                # Payline returns a "REFUSED" code, even though "REFUSED" is
                # supposed to be definitive
                # For our purposes we must consider this case as "in progress"
                return PaymentStatus.Initiated
            if self.code == "02324":
                return PaymentStatus.Expired
            return PaymentStatus.Refused
        if self.short_message == "ERROR":
            return PaymentStatus.Refused

        return PaymentStatus.Initiated

    def is_accepted(self) -> bool:
        """Checks whether the call was successful

        :return: True if successful (return message 'ACCEPTED'), False for any other
        """
        return self.payment_status() == PaymentStatus.Approved


class PaymentRequest:
    """
    Response from a payment creation request
    """

    def __init__(self):
        """Constructor"""

        self.result: PaymentResult = PaymentResult()
        """Whether the request has succeeded, or why it has not"""
        self.token: str = ""
        """ Time stamped token that identifies the merchant's web payment request"""
        self.redirect_url = ""
        """ URL on which the shopper's browser
        must be redirected to make the payment."""


class PaymentDetails:
    """
    Class wrapping the results of a "get payment details" API request

    :param response: Dictionnary containing API call result.
        Must contain a 'result' key.
    """

    def __init__(self, response: Dict[str, Any]):
        """Constructor"""

        self.result: PaymentResult = PaymentResult(response["result"])
        """Whether the request has succeeded, or why it has not"""

        self.response: Dict[str, Any] = response
        """ Dictionary containing the raw SOAP api response for
        a payment details query.
        See https://docs.payline.com/display/DT/Webservice+-+getWebPaymentDetailsResponse
        """

    def raw_metadata(self) -> str:
        """
        :return: the raw response dictionary as a Json string
        """
        return json.dumps(self.response)

    def amount(self) -> decimal.Decimal:
        """
        :return: The payment amount in decimal currency units
        """
        try:
            amount_in_cents = self.payment["amount"]
            return decimal.Decimal(amount_in_cents) / 100
        except (decimal.InvalidOperation, KeyError, TypeError):
            return decimal.Decimal(0)

    @property
    def authorization(self) -> Dict[str, Any]:
        """
        :return: The dictionary corresponding to the "authorization" par of the response
        """
        return self.response.get("authorization", {})

    @property
    def transaction(self) -> Dict[str, Any]:
        """
        See https://docs.payline.com/display/DT/Object+-+transaction

        :return: The dictionary corresponding to the "transaction" par of the response
        """
        return self.response.get("transaction", {})

    @property
    def payment(self) -> Dict[str, Any]:
        """
        See https://docs.payline.com/display/DT/Object+-+payment

        :return: The dictionary corresponding to the "payment" par of the response
        """
        return self.response.get("payment", {})

    @staticmethod
    def from_metadata(raw_metadata: str) -> "PaymentDetails":
        """
        Constructs a PaymentDetails object from a metadata string

        :param: raw_metadata Json-encoded metadata string
        :return: Payment details
        """
        response = json.loads(raw_metadata)
        return PaymentDetails(response)


class RefundDetails:
    """
    Class wrapping the results of a "do refund" API request

    :param response: Dictionnary containing API call result.
        Must contain a 'result' key.
    """

    def __init__(self, response: Dict[str, Any]):
        """Constructor"""

        self.result: PaymentResult = PaymentResult(response["result"])
        """Whether the request has succeeded, or why it has not"""

        self.response: Dict[str, Any] = response
        """ Dictionary containing the raw SOAP api response for
        a payment refund query.
        See https://docs.payline.com/display/DT/Webservice+-+doRefundResponse
        """

    def raw_metadata(self) -> str:
        """
        :return: the raw response dictionary as a Json string
        """
        return json.dumps(self.response)

    @property
    def transaction(self) -> Dict[str, Any]:
        """
        See https://docs.payline.com/display/DT/Object+-+transaction

        :return: The dictionary corresponding to the "transaction" par of the response
        """
        return self.response.get("transaction", {})


class OrderInfo:
    """Class describing an order for a payment request.

    :param payment: Payment database entry, defaults to None
    """

    def unique_ref(self) -> str:
        """
        :return: An unique reference for the order
        """
        if self.payment is None:
            return str(uuid.uuid4())

        # Date with format YYYYMMDD
        date_str = self.payment.creation_time.strftime("%Y%m%d")
        # Activity trigram
        if self.payment.item.event.activity_types:
            activity_str = self.payment.item.event.activity_types[0].trigram
        else:
            activity_str = "NCL"
        # Rolling id making sure we can't get the same ref for distinct orders
        rolling_id = self.payment.id % 10000

        return f"CAF{date_str}{activity_str}{rolling_id:04}"

    def private_data(self) -> Dict[str, Any]:
        """
        :return: Metadata in the Payline key-value list format
        """
        key_value = []
        for key, value in self.metadata.items():
            if isinstance(value, list):
                for i, multi_v in enumerate(value):
                    key_value.append({"key": f"{key}_{i + 1}", "value": multi_v})
            else:
                key_value.append({"key": key, "value": value})

        for pair in key_value:
            ascii_val = to_ascii(pair["value"])
            pair["value"] = ascii_val[:50]

        return {"privateData": key_value}

    def __init__(self, payment: Payment = None):
        """Constructor"""

        self.amount_in_cents: int = 0
        """ Amount in smallest currency unit (e.g euro cents)"""
        self.payment: Payment = None
        """ Related database Payment entry"""
        self.date: str = "01/01/1970 12:34"
        """ Date and time at which the order is being made,
        with format dd/mm/YYYY HH:MM
        """
        self.details: Dict[str, Any] = {}
        """ Dictionary containing details about the order
            See https://docs.payline.com/display/DT/Object+-+orderDetail
        """
        self.metadata: Dict[str, Any] = {}
        """ Dictionnary containing free-form metadata about the order.
            Used in lieu of details as Payline does not seem to acknowledge orderDetails
        """

        if payment is not None:
            self.payment = payment
            self.amount_in_cents = (payment.amount_charged * 100).to_integral_exact()
            self.date = payment.creation_time.strftime("%d/%m/%Y %H:%M")
            item_details = {
                "ref": payment.price.id,
                "comment": truncate(
                    to_ascii(
                        f"{payment.item.event.title} -- {payment.item.title} -- "
                        f"{payment.price.title}"
                    ),
                    max_len=255,
                    append_ellipsis=False,
                ),
                "price": self.amount_in_cents,
            }

            self.details = {"details": [item_details]}
            self.metadata = {
                "collective": payment.item.event.title,
                "collective_id": payment.item.event.id,
                "date": format_date(payment.item.event.start),
                "activite": [a.name for a in payment.item.event.activity_types],
                "objet": payment.item.title,
                "tarif": payment.price.title,
                "encadrants": [
                    u.full_name() for u in payment.item.event.ranked_leaders()
                ],
            }


class BuyerInfo:
    """Information about the user making the payment

    :param payment: User database entry, defaults to None
    """

    def __init__(self, user: User = None):
        """Constructor from an optional user object"""

        self.title: str = ""
        """ Title, e.g. 'M.', 'Mme.', etc"""
        self.last_name: str = ""
        """Buyer last name"""
        self.first_name: str = ""
        """ Buyer first name"""
        self.email: str = ""
        """ Email address, must be valid"""
        self.birth_date: str = ""
        """ Data of birth, ptional"""

        if user is not None:
            self.first_name = user.first_name
            self.last_name = user.last_name
            self.email = user.mail
            if "@" not in user.mail:
                # For testing with admin account
                self.email += "@example.com"

            self.birth_date = user.date_of_birth.strftime("%Y/%m/%d")


class PaylineApi:
    """SOAP Client to process payment with payline, refer to Payline docs"""

    def __init__(self):
        """Constructor"""

        self._webpayment_client: SoapClient = None
        """ SOAP client object to connect to Payline WebPaymentAPI."""
        self._directpayment_client: SoapClient = None
        """ SOAP client object to connect to Payline DirectPaymentAPI."""

        self.payline_currency: str = ""
        """ payment currency : euro = 978"""
        self.payline_contract_number: str = ""
        """ payline contract number"""
        self.payline_merchant_id: str = ""
        """ Payline merchant id refer to payline account"""
        self.payline_merchant_name: str = ""
        """ Payline merchant name"""
        self.payline_access_key: str = ""
        """ Payline access key (to be set in payline backoffice)"""
        self.payline_country: str = ""
        """ Payline country code"""

    def init_app(self, app: Flask):
        """Initialize the payline with the app.
        :param app: Current app.
        """
        pass

    def reload_config(self):
        """Reads current configuration, reset client if necessary"""

        merchant_id_changed = (
            self.payline_merchant_id != Configuration.PAYLINE_MERCHANT_ID
        )

        self.payline_merchant_id = Configuration.PAYLINE_MERCHANT_ID
        self.payline_access_key = Configuration.PAYLINE_ACCESS_KEY
        self.payline_currency = Configuration.PAYLINE_CURRENCY
        self.payline_contract_number = Configuration.PAYLINE_CONTRACT_NUMBER
        self.payline_merchant_name = Configuration.PAYLINE_MERCHANT_NAME
        self.payline_country = Configuration.PAYLINE_COUNTRY

        if merchant_id_changed:
            # Reset clients
            self._webpayment_client = None
            self._directpayment_client = None
            if self.disabled():
                current_app.logger.warning("Payment API disabled, using mock API")

    @property
    def encoded_auth(self):
        """authentication string for http http_header"""
        return base64.b64encode(
            self.payline_merchant_id.encode() + b":" + self.payline_access_key.encode()
        ).decode("utf-8")

    def _create_client(self, wsdl_path: str) -> SoapClient:
        """Creates a SOAP client from a WSDL file

        :param wsdl_path: Relative path to the wsdl file
        """

        return SoapClient(
            wsdl=wsdl_path,
            wsdl_basedir=".",
            http_headers={
                "Authorization": f"Basic {self.encoded_auth}",
                "Content-Type": "text/plain",
            },
        )

    @property
    def webpayment_client(self) -> SoapClient:
        """Cached SOAP client object to connect to Payline WebPaymentAPI."""
        if self._webpayment_client is None:
            self._webpayment_client = self._create_client(
                wsdl_path=current_app.config["PAYLINE_WSDL"],
            )

        return self._webpayment_client

    @property
    def directpayment_client(self) -> SoapClient:
        """Cached SOAP client object to connect to Payline DirectPaymentAPI."""
        if self._directpayment_client is None:
            self._directpayment_client = self._create_client(
                wsdl_path=current_app.config["PAYLINE_DIRECTPAYMENT_WSDL"],
            )

        return self._directpayment_client

    def do_web_payment(
        self, order_info: OrderInfo, buyer_info: BuyerInfo
    ) -> PaymentRequest:
        """Initiates a payment request with Payline and returns the
        resulting token identifier on success, or information about the error

        :param order_info: Information about the item being ordered
        :param buyer_info: Information about the user amking the order
        :return: An object representing the API response, or None if the API call failed
        """
        self.reload_config()

        payment_response = PaymentRequest()

        if self.disabled():
            # Dev mode, every payment is valid with fake token
            payment_response.result.code = "00000"
            payment_response.result.short_message = "ACCEPTED"
            payment_response.token = str(uuid.uuid4())
            payment_response.redirect_url = url_for(
                "payment.do_mock_payment", token=payment_response.token
            )

            return payment_response

        try:
            response = self.webpayment_client.doWebPayment(
                version=PAYLINE_VERSION,
                payment={
                    "amount": order_info.amount_in_cents,
                    "currency": self.payline_currency,
                    "action": PAYMENT_ACTION,
                    "mode": PAYMENT_MODE,
                    "contractNumber": self.payline_contract_number,
                },
                returnURL=url_for("payment.process", _external=True),
                cancelURL=url_for("payment.cancel", _external=True),
                notificationURL=url_for("payment.notify", _external=True),
                order={
                    "ref": order_info.unique_ref(),
                    "amount": order_info.amount_in_cents,
                    "currency": self.payline_currency,
                    "date": order_info.date,
                    "details": order_info.details,
                    "country": self.payline_country,
                },
                selectedContractList=[
                    {"selectedContract": self.payline_contract_number}
                ],
                buyer={
                    "title": buyer_info.title,
                    "lastName": buyer_info.last_name,
                    "firstName": buyer_info.first_name,
                    "email": buyer_info.email,
                    "birthDate": buyer_info.birth_date,
                },
                merchantName=self.payline_merchant_name,
                privateDataList=order_info.private_data(),
                securityMode="SSL",
            )
            payment_response.result = PaymentResult(response["result"])

            if payment_response.result.is_accepted():
                payment_response.token = response["token"]
                payment_response.redirect_url = response["redirectURL"]

            return payment_response

        except pysimplesoap.client.SoapFault as err:
            current_app.logger.error(f"Payment API error: {err}")

        return None

    def get_web_payment_details(self, token: str) -> PaymentDetails:
        """Returns the details about a payment that has been previously initiated

        :param token: The unique identifer returned by the :py:meth:`do_web_payment()` call
        :return: An object representing the payment details, or None if the API call failed
        """
        self.reload_config()

        if self.disabled():
            # Dev mode, result is read from url parameters
            message = request.args.get("message")
            amount = request.args.get("amount")
            response = {
                "result": {
                    "code": "00000",
                    "shortMessage": message,
                    "longMessage": message,
                },
                "transaction": {"id": "12345678", "date": "02/05/2020 22:00:00"},
                "authorization": {"number": "A55A"},
                "payment": {"amount": amount},
            }
            return PaymentDetails(response)

        try:
            response = self.webpayment_client.getWebPaymentDetails(
                version=PAYLINE_VERSION, token=token
            )
            return PaymentDetails(response)

        except pysimplesoap.client.SoapFault as err:
            current_app.logger.error(f"Payment API error: {err}")

        return None

    def do_refund(self, payment_details: PaymentDetails) -> RefundDetails:
        """Tries to refund a previously approved online payment.

        Will first try a 'reset' call (cancel immediately the payment if it has not
        been debited yet), and if this fail will try a full 'refund' call.

        :param payment_details: The payment details as returned by :py:meth:`getWebPaymentDetails`
        :return: An object representing the response details, or None if the API call failed
        """
        self.reload_config()

        if self.disabled():
            # Dev mode, refund always succeeds
            response = {
                "result": {
                    "code": "00000",
                    "shortMessage": "ACCEPTED",
                    "longMessage": "Transaction accepted",
                },
                "transaction": {"id": "12345678", "date": "02/05/2020 22:00:00"},
            }
            return RefundDetails(response)

        try:
            # First try reset in case payment has not been debited yet
            response = self.directpayment_client.doReset(
                version=PAYLINE_VERSION, transactionID=payment_details.transaction["id"]
            )

            # If payment has already been debited, try full refund
            if response["result"]["code"] == "01917":
                response = self.directpayment_client.doRefund(
                    version=PAYLINE_VERSION,
                    transactionID=payment_details.transaction["id"],
                    payment=payment_details.payment,
                )

            return RefundDetails(response)

        except pysimplesoap.client.SoapFault as err:
            current_app.logger.error(f"Payment API error: {err}")

        return None

    def disabled(self) -> bool:
        """Check if Payline merchant Id has been set.
        :return: True if PaylineApi is disabled.
        """
        return not self.payline_merchant_id


api: PaylineApi = PaylineApi()
""" PaylineApi object that will handle request to Payline.

`api` requires to be initialized with :py:meth:`PaylineApi.init_app` to be used.
"""
