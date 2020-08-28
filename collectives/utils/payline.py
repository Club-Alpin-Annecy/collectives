"""Module to handle connexions to Payline.
"""
from sys import stderr
import base64
import json
import decimal
import uuid

from flask import url_for, request, current_app

import pysimplesoap
from pysimplesoap.client import SoapClient

from ..models.payment import PaymentStatus

PAYLINE_VERSION = 24
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


class OrderInfo:
    """Class describing an order for a payment request.
    Will usually be constructed from a :py:class:`collectives.models.payment.Payment` object
    """

    amount_in_cents = 0
    """ Amount in smallest currency unit (e.g euro cents)

    :type: int
    """

    payment_id = 0
    """ Primary key of related database Payment entry

    :type: int
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

    def unique_ref(self):
        """
        :return: An unique reference for the order
        :rtype: string
        """
        return f"order_{self.payment_id}"

    def __init__(self, payment=None):
        """Constructor from an optional payment object

        :param payment: Payment database entry, defaults to None
        :type payment: :py:class:`collectives.models.payment.Payment`, optional
        """
        if payment is not None:
            self.payment_id = payment.id
            self.amount_in_cents = (payment.amount_charged * 100).to_integral_exact()
            self.date = payment.creation_time.strftime("%d/%m/%Y %H:%M")
            item_details = {
                "ref": payment.price.id,
                "comment": f"{payment.item.event.title} -- {payment.item.title} -- {payment.price.title}",
                "price": self.amount_in_cents,
            }
            self.details = {"details": item_details}


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
    """ Emial address, must be valid

    :type: string
    """
    mobilePhone = ""
    """ Mobile phone number, optional

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

            self.mobilePhone = user.phone
            self.birthDate = user.date_of_birth.strftime("%Y/%m/%d")


class PaylineApi:
    """SOAP Client to process payment with payline, refer to Payline docs"""

    soap_client = None
    """ SOAP client object user to connect to Payline client.

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
        if not self.soap_client is None:
            # Already initialized
            return

        config = self.app.config
        if not config["PAYLINE_MERCHANT_ID"]:
            print("Warning: Payment API disabled, using mock API", file=stderr)
            return

        self.payline_merchant_id = config["PAYLINE_MERCHANT_ID"]
        self.payline_access_key = config["PAYLINE_ACCESS_KEY"]
        encoded_auth = base64.b64encode(
            self.payline_merchant_id.encode() + b":" + self.payline_access_key.encode()
        ).decode("utf-8")
        self.payline_currency = config["PAYLINE_CURRENCY"]
        self.payline_contract_number = config["PAYLINE_CONTRACT_NUMBER"]
        self.payline_merchant_name = config["PAYLINE_MERCHANT_NAME"]
        self.payline_country = config["PAYLINE_COUNTRY"]

        try:
            soap_client = SoapClient(
                wsdl=config["PAYLINE_WSDL"],
                http_headers={
                    "Authorization": "Basic %s" % encoded_auth,
                    "Content-Type": "text/plain",
                },
            )
            self.soap_client = soap_client

        except pysimplesoap.client.SoapFault as err:
            print("Extranet API error: {}".format(err), file=stderr)
            self.soap_client = None
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
            response = self.soap_client.doWebPayment(
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
                selectedContractList={"selectedContract": self.payline_contract_number},
                buyer={
                    "title": buyer_info.title,
                    "lastName": buyer_info.lastName,
                    "firstName": buyer_info.firstName,
                    "email": buyer_info.email,
                    "mobilePhone": buyer_info.mobilePhone,
                    "birthDate": buyer_info.birthDate,
                },
                merchantName=self.payline_merchant_name,
                securityMode="SSL",
            )

            payment_response.result = PaymentResult(response["result"])

            payment_response.token = response["token"]
            payment_response.redirect_url = response["redirectURL"]

            return payment_response

        except pysimplesoap.client.SoapFault as err:
            current_app.logger.error("Payment API error: %s", err)

        return None

    def getWebPaymentDetails(self, token):
        """Returns the details about a payment that has been previously initiated

        :param token: The unique identifer returned by the :py:meth:`doWebPayment()` call
        :type token: string
        :return: An object representing the payment details, or None if the API call failed
        :rtype: :py:class:`collectives.utils.payline.PaymentDetails`
        """
        self.init()
        payment_details_response = PaymentDetails()

        if self.disabled():
            # Dev mode, result is read from url parameters
            message = request.args.get("message")
            amount = request.args.get("amount")
            payment_details_response.result.code = "00000"
            payment_details_response.result.short_message = message
            payment_details_response.result.long_message = message

            payment_details_response.transaction["id"] = "12345678"
            payment_details_response.transaction["date"] = "02/05/2020 22:00:00"

            payment_details_response.authorization["number"] = "A55A"
            payment_details_response.payment["amount"] = amount
            return payment_details_response

        try:
            response = self.soap_client.getWebPaymentDetails(
                version=PAYLINE_VERSION, token=token
            )

            payment_details_response.result = PaymentResult(response["result"])
            payment_details_response.response = response

            return payment_details_response

        except pysimplesoap.client.SoapFault as err:
            current_app.logger.error("Payment API error: %s", err)

        return None

    def disabled(self):
        """Check if soap client has been initialized.

        If soap client has not been initialized, it means we are in dev mode.

        :return: True if PaylineApi is disabled.
        :rtype: boolean
        """
        return self.soap_client is None


api = PaylineApi()
""" PaylineApi object that will handle request to Payline.

`api` requires to be initialized with :py:meth:`PaylineApi.init_app` to be used.

:type: :py:class:`PaylineApi`
"""
