"""Module to handle connexions to Payline.
"""
from sys import stderr
import base64
import json

from flask import url_for

import pysimplesoap
from pysimplesoap.client import SoapClient


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
CPT stand for "Full"
:type: string
"""


class PaymentResult:
    """ result returned after payline payment request
    """

    code = ""
    """ return code

    :type :string
    """
    short_message = ""
    """ short message of transaction status
    i.e. : ACCEPTED, REFUSED, ERROR...

    :type :string
    """
    long_message = ""
    """ long message of transaction status details

    :type :string
    """

    partner_code = ""
    """ Return code from partner (payment method) and SAA acquirer

    :type :string
    """
    partner_code_label = ""
    """ Description of the partner error code

    :type :string
    """

class PaymentRequest:
    result = PaymentResult()

    token = ""
    """ Time stamped token that identifies the merchant's web payment request

    :type :string
    """
    redirect_url = ""
    """ URL on which the shopper's browser
    must be redirected to make the payment.

    :type :string
    """

class PaymentDetails:

    result = PaymentResult()

    response = {}
    response["transaction"] = {}
    response["authorization"] = {}

    def raw_metadata(self):
        return json.dumps(self.response)

    @property
    def authorization(self):
        return self.response["authorization"]

    @property
    def transaction(self):
        return self.response["transaction"]


class OrderInfo:
    amount_in_cents = 0
    """ Amount in smallest currency unit (e.g euro cents)
        :type: int
    """

    payment_id = 0
    """ Primary key of related database Payment entry
        :type: int
    """

    date = "1970/1/1"

    details = ""

    def unique_ref(self):
        return f"order_{self.payment_id}"

    def __init__(self, payment=None):
        if payment is not None:
            self.amount = payment.amount
            self.payment_id = payment.id
            self.date = payment.creation_date
            self.amount_in_cents = (payment.amount_charged * 100).to_integral_exact
            self.date = payment.creation_date.strftime("%Y/%m/%d, %H:%M:%S")
            self.details = f"{payment.item.event.title} -- {payment.item.title} -- {payment.price.title}"


class BuyerInfo:
    title = ""
    lastName = ""
    firstName = ""
    email = ""
    mobilePhone = ""
    birthDate = ""

    def __init__(self, user=None):
        if user is not None:
            self.firstName = user.first_name
            self.lastName = user.last_name
            self.email = user.mail
            self.mobilePhone = user.phone
            self.birthDate = user.date_of_birth.strftime("%Y/%m/%d")


class PaylineApi:
    """ SOAP Client to process payment with payline, refer to Payline docs
    """

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

    :type :string
    """

    payline_currency = ""
    """ payment currency : euro = 978

    :type :string
    """

    payline_contract_number = ""
    """ payline contract number

    :type :string
    """

    payline_merchant_id = ""
    """ Payline merchant id refer to payline account

    :type :string
    """

    payline_merchant_name = ""
    """ Payline merchant name

    :type :string
    """

    payline_access_key = ""
    """ Payline access key (to be set in payline backoffice)

    :type :string
    """

    payline_country = ""
    """ Payline country code

    :type :string
    """

    def init_app(self, app):
        """ Initialize the payline with the app.

        :param app: Current app.
        :type app: :py:class:`flask.Flask`
        """
        self.app = app

    def init(self):
        """ Initialize the SOAP Client using `app` config.
        """
        if not self.soap_client is None:
            # Already initialized
            return

        config = self.app.config
        if config["PAYMENTS_ENABLED"]:
            print("Warning: Payment API disabled, using mock API", file=stderr)
            return

        self.payline_merchant_id = config["PAYLINE_MERCHANT_ID"]
        self.payline_access_key = config["PAYLINE_ACCESS_KEY"]
        encoded_auth = base64.b64encode(
            self.payline_merchant_id.encode() + b':' + self.payline_access_key.encode()
        ).decode("utf-8")
        self.payline_currency = config["PAYLINE_CURRENCY"]
        self.payline_contract_number = config["PAYLINE_CONTRACT_NUMBER"]
        self.payline_merchant_name = config["PAYLINE_MERCHANT_NAME"]
        self.payline_country = config["PAYLINE_COUNTRY"]

        try:
            soap_client = SoapClient(
                wsdl='file:./collectives/utils/payline.wsdl',
                http_headers={'Authorization': 'Basic %s' % encoded_auth, 'Content-Type':'text/plain'}
            )
            self.soap_client = soap_client

        except pysimplesoap.client.SoapFault as err:
            print("Extranet API error: {}".format(err), file=stderr)
            self.soap_client = None
            raise err

    def doWebPayment(self, order_info, buyer_info):
        """ Ask Payline to Initialize payment
        """
        self.init()

        payment_response = PaymentRequest()

        if self.disabled():
            # Dev mode, every payment is valid with fake token
            payment_response.result.code = "00000"
            payment_response.result.short_message = "ACCEPTED"
            payment_response.token = "123456789"

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
                returnURL=url_for(
                    "payment.process", payment_id=order_info.payment_id, _external=True
                ),
                cancelURL=url_for(
                    "payment.cancel", payment_id=order_info.payment_id, _external=True
                ),
                notificationURL=url_for(
                    "payment.notify", payment_id=order_info.payment_id, _external=True
                ),
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
                    "birthDate": buyer_info.birthDate
                },
                merchantName=self.payline_merchant_name,
                securityMode="SSL"
            )

            payment_response.result.code = response["result"]["code"]
            payment_response.result.long_message = response["result"]["longMessage"]
            payment_response.result.short_message = response["result"]["shortMessage"]
            payment_response.token = response["token"]
            payment_response.redirect_url = response["redirectURL"]

            return payment_response

        except pysimplesoap.client.SoapFault as err:
            print("Payment API error: {}".format(err), file=stderr)

        return payment_response

    def getWebPaymentDetails(self, token):
        """ Get details for a payment transaction by token
        """
        self.init()
        payment_details_response = PaymentDetails()

        if self.disabled():
            # Dev mode, every payment is valid
            payment_details_response.result.code = "0000"
            payment_details_response.result.short_message = "ACCEPTED"
            payment_details_response.result.long_message = "ACCEPTED"
            payment_details_response.result.partner_code = ""
            payment_details_response.result.partner_code_label = ""

            payment_details_response.transaction["id"] = "12345678"
            payment_details_response.transaction["date"] = "02/05/2020 22:00:00"
            payment_details_response.transaction["isDuplicated"] = "0"
            payment_details_response.transcation["isPossibleFraud"] = "0"
            payment_details_response.transaction["fraudResult"] = ""
            payment_details_response.transaction["explanation"] = ""
            payment_details_response.transaction["threeDSecure"] = "N"
            payment_details_response.transaction["softDescriptor"] = ""
            payment_details_response.transaction["score"] = ""

            payment_details_response.authorization["number"] = "A55A"
            payment_details_response.authorization["date"] = "02/05/2020 22:00:00"
            return payment_details_response

        try:
            response = self.soap_client.getWebPaymentDetails(
                version=PAYLINE_VERSION, token=token
            )

            payment_details_response.result.code = response["result"]["code"]
            payment_details_response.result.short_message = response["result"]["shortMessage"]
            payment_details_response.result.long_message = response["result"]["longMessage"]

            payment_details_response.response = response

            return payment_details_response

        except pysimplesoap.client.SoapFault as err:
            print("Payline API error: {}".format(err), file=stderr)

        return payment_details_response

    def disabled(self):
        """ Check if soap client has been initialized.

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
