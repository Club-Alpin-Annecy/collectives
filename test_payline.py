
from collectives import create_app

from collectives.utils import payline

def test_dowebpayment():

    order = payline.OrderInfo()

    order.payment_id = 2
    order.amount_in_cents = "10000"
    order.date = "05/05/2020 00:05"

    buyer = payline.BuyerInfo()

    buyer.title = "4"
    buyer.lastName = "DO"
    buyer.firstName = "JOHN"
    buyer.email = "johndoe@yopmail.com"
    buyer.mobilePhone = "0600000000"
    buyer.birthDate = "1980-01-20"

    doWebPaymentResponse = payline.api.doWebPayment(order, buyer)
    if not doWebPaymentResponse is None:
        print('token : %s, URL de paiement : %s' % (doWebPaymentResponse.token, doWebPaymentResponse.redirect_url))

        input("appuyer sur une touche lorsque le paiement est validé")

        getWebPaymentDetailsResponse = payline.api.getWebPaymentDetails(doWebPaymentResponse.token)

        if not getWebPaymentDetailsResponse is None:
            print('%s %s %s' % (getWebPaymentDetailsResponse.result.short_message, getWebPaymentDetailsResponse.authorization["number"], getWebPaymentDetailsResponse.authorization["date"]))
            print(getWebPaymentDetailsResponse.raw_metadata())

if __name__ == "__main__":
    app = create_app()
    app.config["SERVER_NAME"] = "localhost"
    with app.app_context():
        test_dowebpayment()
