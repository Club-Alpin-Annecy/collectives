"""Module to handle connexions to Payline.
"""
import base64
import json
import decimal
import uuid

from flask import url_for, request, current_app

import pysimplesoap
from pysimplesoap.client import SoapClient

from ..models.payment import PaymentStatus
from ..models import Configuration
from .time import format_date
from .misc import to_ascii

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
    """

    code = ""
    """ Return code, see https://docs.payline.com/display/DT/Return+codes

    :type: string
    """
    short_message = ""
    """ short message of transaction status
    i.e. : ACCEPTED, REFUSED, ERROR...
    See https://docs.payline.com/display/DT/Codes+-+ShortMessage

    :type: string
    """
    long_message = ""
    """ long message of transaction status details

    :type: string
    """

    def __init__(self, response=None):
        """Constructor from an optional SOAP response dictionary

        :param response: Result object from SOAP response
        :type response: dict
        """
        if response is not None:
            self.code = response["code"]
            self.long_message = response["longMessage"]
            self.short_message = response["shortMessage"]

    def payment_status(self):
        """Maps the API response short message and code to
        a value from our PaymentStatus enum.

        :return: The corresponding payment status
        :rtype: :py:class:`collectives.models.payment.PaymentStatus`
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

    def is_accepted(self):
        """Checks whether the call was successful

        :return: True if successful (return message 'ACCEPTED'), False for any other
        :rtype: bool
        """
        return self.payment_status() == PaymentStatus.Approved


class PaymentRequest:
    """
    Response from a payment creation request
    """

    result = PaymentResult()
    """
    Whether the request has succeeded, or why it has not

    :type: :py:class:`collectives.utils.payline.PaymentResult`
    """

    token = ""
    """ Time stamped token that identifies the merchant's web payment request

    :type: string
    """
    redirect_url = ""
    """ URL on which the shopper's browser
    must be redirected to make the payment.

    :type: string
    """


class PaymentDetails:
    """
    Class wrapping the results of a "get payment details" API request
    """

    result = PaymentResult()
    """
    Whether the request has succeeded, or why it has not

    :type: :py:class:`collectives.utils.payline.PaymentResult`
    """

    response = {}
    """ Dictionary containing the raw SOAP api response for
    a payment details query.
    See https://docs.payline.com/display/DT/Webservice+-+getWebPaymentDetailsResponse

    :type: dict
    """

    response["transaction"] = {}
    response["authorization"] = {}
    response["payment"] = {}

    def raw_metadata(self):
        """
        :return: the raw response dictionary as a Json string
        :rtype: string
        """
        return json.dumps(self.response)

    def amount(self):
        """
        :return: The payment amount in decimal currency units
        :rtype: :py:class:`decimal.Decimal`
        """
        try:
            amount_in_cents = self.payment["amount"]
            return decimal.Decimal(amount_in_cents) / 100
        except (decimal.InvalidOperation, KeyError, TypeError):
            return decimal.Decimal(0)

    @property
    def authorization(self):
        """
        :return: The dictionary corresponding to the "authorization" par of the response
        :rtype: dict
        """
        return self.response["authorization"]

    @property
    def transaction(self):
        """
        See https://docs.payline.com/display/DT/Object+-+transaction

        :return: The dictionary corresponding to the "transaction" par of the response
        :rtype: dict
        """
        return self.response["transaction"]

    @property
    def payment(self):
        """
        See https://docs.payline.com/display/DT/Object+-+payment

        :return: The dictionary corresponding to the "payment" par of the response
        :rtype: dict
        """
        return self.response["payment"]

    @staticmethod
    def from_metadata(raw_metadata):
        """
        Constructs a PaymentDetails object from a metadata string

        :param: raw_metadata Json-encoded metadata string
        :type: raw_metadata string
        :return: Payment details
        :rtype: :py:class:`collectives.utils.payline.PaymentDetails`
        """
        response = json.loads(raw_metadata)
        return PaymentDetails(response)

    def __init__(self, response):
        """
        Constructor from response dictionnary

        :param: response Dictionnary containing API call result
        :type: response dict
        """
        self.result = PaymentResult(response["result"])
        self.response = response


class RefundDetails:
    """
    Class wrapping the results of a "do refund" API request
    """

    result = PaymentResult()
    """
    Whether the request has succeeded, or why it has not

    :type: :py:class:`collectives.utils.payline.PaymentResult`
    """

    response = {}
    """ Dictionary containing the raw SOAP api response for
    a payment details query.
    See https://docs.payline.com/display/DT/Webservice+-+doRefundResponse

    :type: dict
    """

    response["transaction"] = {}

    def raw_metadata(self):
        """
        :return: the raw response dictionary as a Json string
        :rtype: string
        """
        return json.dumps(self.response)

    @property
    def transaction(self):
        """
        See https://docs.payline.com/display/DT/Object+-+transaction

        :return: The dictionary corresponding to the "transaction" par of the response
        :rtype: dict
        """
        return self.response["transaction"]

    def __init__(self, response):
        """
        Constructor from response dictionnary

        :param: response Dictionnary containing API call result
        :type: response dict
        """
        self.result = PaymentResult(response["result"])
        self.response = response


class OrderInfo:
    """Class describing an order for a payment request.
    Will usually be constructed from a :py:class:`collectives.models.payment.Payment` object
    """

    amount_in_cents = 0
    """ Amount in smallest currency unit (e.g euro cents)

    :type: int
    """

    payment = None
    """ Related database Payment entry

    :type: :py:class:`collectives.models.payment.Payment`
    """

    date = "01/01/1970 13:25"
    """ Date and time at which the order is being made,
    with format dd/mm/YYYY HH:MM

    :type: string
    """

    details = {}
    """ Dictionary containing details about the order
        See https://docs.payline.com/display/DT/Object+-+orderDetail

        :type: dict
    """

    metadata = {}
    """ Dictionnary containing free-form metadata about the order.
        Used in lieu of details as Payline does not seem to acknowledge orderDetails

        :type: dict
    """

    def unique_ref(self):
        """
        :return: An unique reference for the order
        :rtype: string
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

    def private_data(self):
        """
        :return: Metadata in the Payline key-value list format
        :rtype: dict
        """
        kv = []
        for k, v in self.metadata.items():
            if isinstance(v, list):
                for i, multi_v in enumerate(v):
                    kv.append({"key": f"{k}_{i+1}", "value": multi_v})
            else:
                kv.append({"key": k, "value": v})

        for pair in kv:
            ascii_val = to_ascii(pair["value"])
            pair["value"] = ascii_val[:50]

        return {"privateData": kv}

    def __init__(self, payment=None):
        """Constructor from an optional payment object

        :param payment: Payment database entry, defaults to None
        :type payment: :py:class:`collectives.models.payment.Payment`, optional
        """
        if payment is not None:
            self.payment = payment
            self.amount_in_cents = (payment.amount_charged * 100).to_integral_exact()
            self.date = payment.creation_time.strftime("%d/%m/%Y %H:%M")
            item_details = {
                "ref": payment.price.id,
                "comment": f"{payment.item.event.title} -- {payment.item.title} -- {payment.price.title}",
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
    """Information about the user making the payment"""

    title = ""
    """ Title, e.g. 'M.', 'Mme.', etc

    :type: string
    """
    lastName = ""
    """ Buyer last name

    :type: string
    """
    firstName = ""
    """ Buyer first name

    :type: string
    """
    email = ""
    """ Email address, must be valid

    :type: string
    """
    birthDate = ""
    """ Data of birth, ptional

    :type: string
    """

    def __init__(self, user=None):
        """Constructor from an optional user object

        :param payment: User database entry, defaults to None
        :type payment: :py:class:`collectives.models.user.User`, optional
        """
        if user is not None:
            self.firstName = user.first_name
            self.lastName = user.last_name
            self.email = user.mail
            if "@" not in user.mail:
                # For testing with admin account
                self.email += "@example.com"

            self.birthDate = user.date_of_birth.strftime("%Y/%m/%d")


class PaylineApi:
    """SOAP Client to process payment with payline, refer to Payline docs"""

    webpayment_client = None
    """ SOAP client object to connect to Payline WebPaymentAPI.

    :type: :py:class:`pysimplesoap.client.SoapClient`
    """

    directpayment_client = None
    """ SOAP client object to connect to Payline DirectPaymentAPI.

    :type: :py:class:`pysimplesoap.client.SoapClient`
    """

    app = None
    """ Current flask application.

    :type: :py:class:`flask.Flask`
    """

    encoded_auth = ""
    """ authentication string for http http_header

    :type: string
    """

    payline_currency = ""
    """ payment currency : euro = 978

    :type: string
    """

    payline_contract_number = ""
    """ payline contract number

    :type: string
    """

    payline_merchant_id = ""
    """ Payline merchant id refer to payline account

    :type: string
    """

    payline_merchant_name = ""
    """ Payline merchant name

    :type: string
    """

    payline_access_key = ""
    """ Payline access key (to be set in payline backoffice)

    :type: string
    """

    payline_country = ""
    """ Payline country code

    :type: string
    """

    def init_app(self, app):
        """Initialize the payline with the app.

        :param app: Current app.
        :type app: :py:class:`flask.Flask`
        """
        self.app = app

    def init(self):
        """Initialize the SOAP Client using `app` config."""
        if not self.webpayment_client is None:
            # Already initialized
            return

        if not Configuration.PAYLINE_MERCHANT_ID:
            current_app.logger.warning("Payment API disabled, using mock API")
            return

        self.payline_merchant_id = Configuration.PAYLINE_MERCHANT_ID
        self.payline_access_key = Configuration.PAYLINE_ACCESS_KEY
        encoded_auth = base64.b64encode(
            self.payline_merchant_id.encode() + b":" + self.payline_access_key.encode()
        ).decode("utf-8")
        self.payline_currency = Configuration.PAYLINE_CURRENCY
        self.payline_contract_number = Configuration.PAYLINE_CONTRACT_NUMBER
        self.payline_merchant_name = Configuration.PAYLINE_MERCHANT_NAME
        self.payline_country = Configuration.PAYLINE_COUNTRY

        try:
            self.webpayment_client = SoapClient(
                wsdl=current_app.config["PAYLINE_WSDL"],
                http_headers={
                    "Authorization": f"Basic {encoded_auth}",
                    "Content-Type": "text/plain",
                },
            )
            self.directpayment_client = SoapClient(
                wsdl=current_app.config["PAYLINE_DIRECTPAYMENT_WSDL"],
                http_headers={
                    "Authorization": f"Basic {encoded_auth}",
                    "Content-Type": "text/plain",
                },
            )

        except pysimplesoap.client.SoapFault as err:
            current_app.logger.error(f"Extranet API error: {err}")
            self.webpayment_client = None
            self.directpayment_client = None
            raise err

    def doWebPayment(self, order_info, buyer_info):
        """Initiates a payment request with Payline and returns the
        resulting token identifier on success, or information about the error

        :param order_info: Information about the item being ordered
        :type order_info: :py:class:`collectives.utils.payline.OrderInfo`
        :param buyer_info: Information about the user amking the order
        :type buyer_info: :py:class:`collectives.utils.payline.OrderInfo`
        :return: An object representing the API response, or None if the API call failed
        :rtype: :py:class:`collectives.utils.payline.PaymentRequest`
        """
        self.init()

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
                    "lastName": buyer_info.lastName,
                    "firstName": buyer_info.firstName,
                    "email": buyer_info.email,
                    "birthDate": buyer_info.birthDate,
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

    def getWebPaymentDetails(self, token):
        """Returns the details about a payment that has been previously initiated

        :param token: The unique identifer returned by the :py:meth:`doWebPayment()` call
        :type token: string
        :return: An object representing the payment details, or None if the API call failed
        :rtype: :py:class:`collectives.utils.payline.PaymentDetails`
        """
        self.init()

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

    def doRefund(self, payment_details):
        """Tries to refund a previously approved online payment.

        Will first try a 'reset' call (cancel immediately the payment if it has not
        been debited yet), and if this fail will try a full 'refund' call.

        :param payment_details: The payment details as returned by :py:meth:`getWebPaymentDetails`
        :type token: :py:class:`collectives.utils.payline.PaymentDetails`
        :return: An object representing the response details, or None if the API call failed
        :rtype: :py:class:`collectives.utils.payline.RefundDetails`
        """
        self.init()

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

    def disabled(self):
        """Check if soap client has been initialized.

        If soap client has not been initialized, it means we are in dev mode.

        :return: True if PaylineApi is disabled.
        :rtype: boolean
        """
        return self.webpayment_client is None


api = PaylineApi()
""" PaylineApi object that will handle request to Payline.

`api` requires to be initialized with :py:meth:`PaylineApi.init_app` to be used.

:type: :py:class:`PaylineApi`
"""
