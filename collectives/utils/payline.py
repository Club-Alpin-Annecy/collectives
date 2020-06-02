"""Module to handle connexions to Payline.
"""
from datetime import datetime, date
from sys import stderr

import pysimplesoap
from pysimplesoap.client import SoapClient

import base64

from ..models import Gender
from .time import current_time


class PaymentAcceptance:
    code = ""
    short_message = ""
    long_message = ""
    token = ""
    redirect_url = ""


class PaymentDetails:

    code = ""
    short_message = ""
    long_message = ""
    partner_code = ""
    partner_code_label = ""

    transaction = {}
    transaction["id"] = ""
    transaction["date"] = ""
    transaction["is_duplicated"] = ""
    transaction["is_possible_fraud"] = ""
    transaction["fraud_result"] = ""
    transaction["explanation"] = ""
    transaction["3DSecure"] = ""
    transaction["soft_descriptor"] = ""
    transaction["score"] = ""

    authorization = {}
    authorization["number"] = ""
    authorization["date"] = ""


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
    web_payment_info = None

    encoded_auth = ""

    payline_version = ""
    payline_currency = ""
    payline_mode = ""
    payline_contract_number = ""
    payline_return_url = ""
    payline_cancel_url = ""
    payline_notification_url = ""
    PAYLINE_merchant_name = ""

    def init_app(self, app):
        """ Initialize the extranet with the app.

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
        if config["PAYMENT_DISABLE"]:
            print("Warning: Payment API disabled, using mock API", file=stderr)
            return
        else:
            self.payline_merchant_id = config["PAYLINE_MERCHANT_ID"]
            self.payline_access_key = config["PAYLINE_ACCESS.KEY"]
            encoded_auth = base64.b64encode(
                self.payline_merchant_id + ":" + self.payline_access_key
            ).decode("utf-8")
            self.payline_version = config["PAYLINE_VERSION"]
            self.payline_currency = config["PAYLINE_CURRENCY"]
            self.payline_mode = config["PAYLINE_MODE"]
            self.payline_contract_number = config["PAYLINE_CONTRACT_NUMBER"]
            self.payline_return_url = config["PAYLINE_RETURN_URL"]
            self.payline_cancel_url = config["PAYLINE_CANCEL_URL"]
            self.payline_notification_url = config["PAYLINE_NOTIFICATION_URL"]
            self.payline_merchant_name = config["PAYLINE_MERCHANT_NAME"]

        try:
            soap_client = SoapClient(
                wsdl=config["PAYLINE_WSDL"],
                http_headers={"Authorization": "Basic %s" % encoded_auth},
            )
            self.soap_client = soap_client

        except pysimplesoap.client.SoapFault as err:
            print("Extranet API error: {}".format(err), file=stderr)
            self.soap_client = None
            raise err

    def doWebPayment(self, order_info, buyer_info):
        """
        """

        payment_response = PaymentAcceptance()

        if self.disabled():
            # Dev mode, every license is valid
            payment_response.code = "0000"
            payment_response.short_message = "ACCEPTED"
            payment_response.token = "123456789"

            return payment_response

        try:
            response = self.soap_client.doWebPayment(
                version=self.payline_version,
                payment={
                    "amount": 100,
                    "currency": self.payline_currency,
                    "action": self.payline_currency,
                    "mode": self.payline_mode,
                    "contractNumber": self.payline_contract_number,
                },
                returnURL=self.payline_return_url,
                cancelURL=self.payline_cancel_url,
                order={
                    "ref": order_info.ref,
                    "amount": order_info.amount,
                    "currency": self.payline_currency,
                    "date": order_info.date,
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
            )

            payment_response.code = response["code"]
            payment_response.long_message = response["long_message"]
            payment_response.token = response["token"]
            payment_response.redirect_url = response["redirect_url"]

        except pysimplesoap.client.SoapFault as err:
            print("Extranet API error: {}".format(err), file=stderr)

    def getWebPaymentDetails(self, token):
        """
        """
        payment_details_response = PaymentDetails()

        if self.disabled():
            # Dev mode, every license is valid
            payment_details_response.code = "0000"
            payment_details_response.short_message = "ACCEPTED"
            payment_details_response.long_message = "ACCEPTED"
            payment_details_response.partner_code = ""
            payment_details_response.partner_code_label = ""

            payment_details_response.transaction["id"] = "12345678"
            payment_details_response.transaction["date"] = "02/05/2020 22:00:00"
            payment_details_response.transaction["is_duplicated"] = "0"
            payment_details_response.transcation["is_possible_fraud"] = "0"
            payment_details_response.transaction["fraud_result"] = ""
            payment_details_response.transaction["explanation"] = ""
            payment_details_response.transaction["3DSecure"] = "N"
            payment_details_response.transaction["soft_descriptor"] = ""
            payment_details_response.transaction["score"] = ""

            payment_details_response.authorization["number"] = "A55A"
            payment_details_response.authorization["date"] = "02/05/2020 22:00:00"
            return payment_details_response

        try:
            response = self.soap_client.getWebPaymentDetails(
                version=self.payline_version, token=token
            )

            payment_details_response.code = response["code"]
            payment_details_response.short_message = response["short_message"]
            payment_details_response.long_message = response["long_message"]
            payment_details_response.partner_code = response["partner_code"]
            payment_details_response.partner_code_label = response["partner_code_label"]

            payment_details_response.transaction["id"] = response["transaction"]["id"]
            payment_details_response.transaction["date"] = response["transaction"][
                "date"
            ]
            payment_details_response.transaction["is_duplicated"] = response[
                "transaction"
            ]["is_duplicated"]
            payment_details_response.transcation["is_possible_fraud"] = response[
                "transaction"
            ]["is_possible_fraud"]
            payment_details_response.transaction["fraud_result"] = response[
                "transaction"
            ]["fraud_result"]
            payment_details_response.transaction["explanation"] = response[
                "transaction"
            ]["explanation"]
            payment_details_response.transaction["3DSecure"] = response["transaction"][
                "3DSecure"
            ]
            payment_details_response.transaction["soft_descriptor"] = response[
                "transaction"
            ]["soft_descriptor"]
            payment_details_response.transaction["score"] = response["transaction"][
                "score"
            ]

            payment_details_response.authorization["number"] = response[
                "authorization"
            ]["number"]
            payment_details_response.authorization["date"] = response["authorization"][
                "date"
            ]

        except pysimplesoap.client.SoapFault as err:
            print("Extranet API error: {}".format(err), file=stderr)

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
