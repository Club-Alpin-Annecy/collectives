

from flask import Flask

import os
import collectives

from collectives.utils import payline

import time

class order_info:
    ref = ""
    amount = ""
    date =""

class buyer_info:
    title = ""
    lastName = ""
    firstName = ""
    email = ""
    mobilePhone = ""
    birthDate = ""

class TestPaylineApi:

    def test_dowebpayment():
        os.environ["FLASK_APP"] = "collectives:create_app"
        """os.system("flask db upgrade")"""



        order = order_info()

        order.ref = "TEST2"
        order.amount = "10000"
        order.date = "05/05/2020 00:05"

        buyer = buyer_info()

        buyer.title = "4"
        buyer.lastName = "DO"
        buyer.firstName = "JOHN"
        buyer.email = "johndoe@yopmail.com"
        buyer.mobilePhone = "0600000000"
        buyer.birthDate = "1980-01-20"

        app = Flask(__name__, instance_relative_config=True)

        # Config options - Make sure you created a 'config.py' file.
        app.config.from_object("config")
        app.config.from_pyfile("config.py")

        paylineAPI = payline.api
        paylineAPI.init_app(app)
        doWebPaymentResponse = paylineAPI.doWebPayment(order, buyer)
        if not doWebPaymentResponse is None:
            print('token : %s, URL de paiement : %s' % (doWebPaymentResponse.token, doWebPaymentResponse.redirect_url))

            wait = input("appuyer sur une touche lorsque le paiement est validé")

            getWebPaymentDetailsResponse = paylineAPI.getWebPaymentDetails(doWebPaymentResponse.token)

            if not getWebPaymentDetailsResponse is None:
                print('%s %s %s' % (getWebPaymentDetailsResponse.short_message, getWebPaymentDetailsResponse.authorization["number"], getWebPaymentDetailsResponse.authorization["date"]))


TestPaylineApi.test_dowebpayment()
