"""Module to handle connexions to Payline.
"""
from sys import stderr

import pysimplesoap
from pysimplesoap.client import SoapClient

import base64

class PaymentAcceptance:
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

    code = ""
    """ return code

    :type :string
    """

    short_message = ""
    """ short message of transaction status details

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

    transaction = {}
    """Transaction Information

    :type :dictionnary
    """
    transaction["id"] = ""
    """Unique Payline transaction identifier

    :type :string
    """
    transaction["date"] = ""
    """ Date and time of Payline transaction

    :type :string
    """
    transaction["is_duplicated"] = ""
    """ This indicator is returned by Payline in case of transaction duplicated

    :type :string
    """
    transaction["is_possible_fraud"] = ""
    """ This indicator is calculated according to the criteria
    defined by the merchant

    :type :string
    """
    transaction["fraud_result"] = ""
    """ Fraud Details

    :type :string
    """
    transaction["explanation"] = ""
    """ Reason for refusal in case of fraud

    :type :string
    """
    transaction["3DSecure"] = ""
    """ This indicator is returned by Payline during 3DSecure transactions

    :type :string
    """
    transaction["soft_descriptor"] = ""
    """
    Information displayed on the account statement of the buyer,
    limited with certain payment method.
    This information will be displayed on the payment ticket.

    :type :string
    """
    transaction["score"] = ""
    """ Fraud scoring value : Score from 0 to 10

    :type :string
    """

    authorization = {}
    """ authorization information

    :type :dictionnary
    """
    authorization["number"] = ""
    """ Authorization number issued by the acquirer authorization server.
    This field is filled in if the authorization request is granted.

    :type :string
    """
    authorization["date"] = ""
    """ Date and time of authorization : Format : dd/mm/yyyy HH24:MI

    :type :string
    """


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

    payline_version = ""
    """ version of Payline API used

    :type :string
    """
    payline_currency = ""
    """ payment currency : euro = 978

    :type :string
    """

    payline_mode = ""
    """ payment mode, Full or Differed :Full = CPT

    :type :string
    """

    payline_contract_number = ""
    """ payline contract number

    :type :string
    """

    payline_return_url = ""
    """ redirect url after a payment form is validated by user

    :type :string
    """
    payline_cancel_url = ""
    """ redirect url after a payment form is cancelled by user

    :type :string
    """
    payline_notification_url = ""
    """ redirect url after no action is performed by user

    :type :string
    """
    payline_merchant_id = ""
    """ Payline merchant id refer to payline account

    :type :string
    """
    Payline_merchant_name = ""
    """ Payline merchant name

    :type :string
    """
    payline_access_key = ""
    """ Payline access key (to be set in payline backoffice)

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
        if config["PAYMENT_DISABLE"]:
            print("Warning: Payment API disabled, using mock API", file=stderr)
            return
        else:
            self.payline_merchant_id = config["PAYLINE_MERCHANT_ID"]
            self.payline_access_key = config["PAYLINE_ACCESS_KEY"]
            encoded_auth = base64.b64encode(
                self.payline_merchant_id.encode() + b':' + self.payline_access_key.encode()
            ).decode("utf-8")
            self.payline_version = config["PAYLINE_VERSION"]
            self.payline_currency = config["PAYLINE_CURRENCY"]
            self.payline_action = config["PAYLINE_ACTION"]
            self.payline_mode = config["PAYLINE_MODE"]
            self.payline_contract_number = config["PAYLINE_CONTRACT_NUMBER"]
            self.payline_return_url = config["PAYLINE_RETURN_URL"]
            self.payline_cancel_url = config["PAYLINE_CANCEL_URL"]
            self.payline_notification_url = config["PAYLINE_NOTIFICATION_URL"]
            self.payline_merchant_name = config["PAYLINE_MERCHANT_NAME"]

        try:
            """wsdl='file:C:/temp/payline.wsdl'"""
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
        payment_response = PaymentAcceptance()

        if self.disabled():
            # Dev mode, every payment is valid with fake token
            payment_response.code = "0000"
            payment_response.short_message = "ACCEPTED"
            payment_response.token = "123456789"

            return payment_response

        try:
            response = self.soap_client.doWebPayment(
                version=self.payline_version,
                payment={
                    "amount": order_info.amount,
                    "currency": self.payline_currency,
                    "action": self.payline_action,
                    "mode": self.payline_mode,
                    "contractNumber": self.payline_contract_number
                },
                returnURL=self.payline_return_url,
                cancelURL=self.payline_cancel_url,
                notificationURL=self.payline_notification_url,
                order={
                    "ref": order_info.ref,
                    "amount": order_info.amount,
                    "currency": self.payline_currency,
                    "date": order_info.date
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
                merchantName=self.payline_merchant_name
            )

            payment_response.code = response["result"]["code"]
            payment_response.short_message = response["result"]["shortMessage"]
            payment_response.long_message = response["result"]["longMessage"]
            payment_response.token = response["token"]
            payment_response.redirect_url = response["redirectURL"]

            return payment_response

        except pysimplesoap.client.SoapFault as err:
            print("Extranet API error: {}".format(err), file=stderr)

    def getWebPaymentDetails(self, token):
        """ Get details for a payment transaction by token
        """
        self.init()
        payment_details_response = PaymentDetails()

        if self.disabled():
            # Dev mode, every payment is valid
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

            payment_details_response.code = response["result"]["code"]
            payment_details_response.short_message = response["result"]["shortMessage"]
            payment_details_response.long_message = response["result"]["longMessage"]

            payment_details_response.transaction["id"] = response["transaction"]["id"]
            payment_details_response.transaction["date"] = response["transaction"][
                "date"
            ]
            payment_details_response.transaction["is_duplicated"] = response[
                "transaction"
            ]["isDuplicated"]
            payment_details_response.transaction["is_possible_fraud"] = response[
                "transaction"
            ]["isPossibleFraud"]
            payment_details_response.transaction["fraud_result"] = response[
                "transaction"
            ]["fraudResult"]
            payment_details_response.transaction["explanation"] = response[
                "transaction"
            ]["explanation"]
            payment_details_response.transaction["3DSecure"] = response["transaction"][
                "threeDSecure"
            ]

            payment_details_response.transaction["score"] = response["transaction"][
                "score"
            ]

            payment_details_response.authorization["number"] = response[
                "authorization"
            ]["number"]
            payment_details_response.authorization["date"] = response["authorization"][
                "date"
            ]

            return payment_details_response

        except pysimplesoap.client.SoapFault as err:
            print("Payline API error: {}".format(err), file=stderr)

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
