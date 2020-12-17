import argparse

from collectives import create_app
from collectives.utils import payline


def doWebPayment():
    """
    Initiates a new Payline web payment.
    :return: The resulting Payline token
    :rtype: str
    """

    order = payline.OrderInfo()

    order.payment_id = 2
    order.amount_in_cents = "10000"
    order.date = "05/05/2020 00:05"
    order.details = {"details": {"ref": "12"}}

    buyer = payline.BuyerInfo()

    buyer.title = "4"
    buyer.lastName = "DO"
    buyer.firstName = "JOHN"
    buyer.email = "johndoe@yopmail.com"
    buyer.mobilePhone = "0600000000"
    buyer.birthDate = "1980-01-20"

    doWebPaymentResponse = payline.api.doWebPayment(order, buyer)
    if doWebPaymentResponse is None:
        raise RuntimeError("Payline API error")

    print(
        "token : %s, URL de paiement : %s"
        % (doWebPaymentResponse.token, doWebPaymentResponse.redirect_url)
    )
    input("appuyer sur une touche lorsque le paiement est validé")

    return doWebPaymentResponse.token


def getPaymentDetails(token):
    """Displays and returns information about a payment

    :param token: The payline token
    :type token: str
    :return: The payment information
    :rtype: :py:class:`collectives.utils.payline.PaymentDetails`
    """
    details = payline.api.getWebPaymentDetails(token)
    print(
        "Result: %s Transaction: %s Date: %s"
        % (
            details.result.short_message,
            details.transaction["id"],
            details.transaction["date"],
        )
    )
    print(details.raw_metadata())
    return details


def doRefund(payment_details):
    """Initiates a refind request

    :param payment_details: Payment details as returned by :py:func:`getPaymentDetails`
    :type payment_details: :py:class:`collectives.utils.payline.PaymentDetails`
    """
    # Try refund
    refundResponse = payline.api.doRefund(payment_details)
    if refundResponse is None:
        raise RuntimeError("Payline API error")

    print(
        "Refund result: %s %s"
        % (
            refundResponse.result.code,
            refundResponse.result.long_message,
        )
    )
    print(refundResponse.raw_metadata())


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--token",
        help="If provided fetch payment information from an existing payline token. Otherwise initiate a new payment",
    )
    parser.add_argument(
        "-r",
        "--refund",
        action="store_true",
        help="If provided attempt to refund the payment",
    )
    args = parser.parse_args()

    app = create_app()
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        payment_token = args.token
        if payment_token is None:
            payment_token = doWebPayment()

        retrieved_details = getPaymentDetails(payment_token)
        if args.refund:
            doRefund(retrieved_details)
