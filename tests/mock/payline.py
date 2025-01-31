"""Mock functions for payline."""

import pytest

# pylint: disable=unused-argument


class FakeSoapClient:
    """Fake Soap Client that will emulate the Payline SoapClient."""

    # pylint: disable=invalid-name
    def doWebPayment(self, **kwargs):
        """Mock the payline SOAP API "doWebPayment"

        :param dict() kwargs: Key word arguments

        :Keyword Arguments:
            * *id* (``dict``) the licence which will be retrieved

        :returns: some data to go pay on payline
        :rtype: dict"""
        return {
            "result": {
                "code": "00000",
                "shortMessage": "ACCEPTED",
                "longMessage": "Transaction approved",
            },
            "token": "1jom6TVNaLuHygEB62681665928911817",
            "redirectURL": (
                "https://homologation-webpayment.payline.com/v2/?"
                "token=1jom6TVNaLuHygEB62681665928911817"
            ),
        }

    def getWebPaymentDetails(self, **kwargs):
        """Mock the payline SOAP API "doWebPayment"

        :param dict() kwargs: Key word arguments

        :Keyword Arguments:
            * *id* (``dict``) the licence which will be retrieved

        :returns: some data related to this license
        :rtype: dict"""
        return {
            "result": {
                "code": "00000",
                "shortMessage": "ACCEPTED",
                "longMessage": "Transaction approved",
            },
            "transaction": {
                "id": "13289144956729",
                "date": "16/10/2022 16:49:56",
                "isDuplicated": "0",
                "isPossibleFraud": "0",
                "fraudResult": None,
                "explanation": None,
                "threeDSecure": "N",
                "score": "0",
                "partnerAdditionalData": None,
                "avs": {"result": "4", "resultFromAcquirer": None},
            },
            "payment": {
                "amount": "1000",
                "currency": "978",
                "action": "101",
                "mode": "CPT",
                "contractNumber": "1234567",
                "differedActionDate": None,
                "method": "CB",
                "cardBrand": None,
            },
            "authorization": {"number": "A55A", "date": "16/10/2022 16:49:56"},
            "privateDataList": {
                "privateData": [
                    {"key": "collective", "value": "ddd"},
                    {"key": "collective_id", "value": "29"},
                    {"key": "date", "value": "samedi 26 novembre 2022"},
                    {"key": "activite_1", "value": "Alpinisme"},
                    {"key": "objet", "value": "Poire"},
                    {"key": "tarif", "value": "Adultes"},
                    {"key": "encadrants_1", "value": "Mike GIBSON"},
                ]
            },
            "paymentRecordId": None,
            "authentication3DSecure": {
                "md": None,
                "xid": None,
                "eci": None,
                "cavv": None,
                "cavvAlgorithm": None,
                "vadsResult": None,
            },
            "card": {
                "number": "497010XXXXXX4149",
                "type": "CB",
                "expirationDate": "0223",
                "panType": None,
            },
            "extendedCard": {
                "country": "FRA",
                "isCvd": None,
                "bank": None,
                "type": "CB",
                "network": "CB",
                "product": "Visa Infinite",
            },
            "order": {
                "ref": "CAF20221016AAL0016",
                "origin": None,
                "country": "FR",
                "amount": "1000",
                "currency": "978",
                "date": "16/10/2022 16:49:00",
                "deliveryTime": None,
                "deliveryMode": None,
                "deliveryExpectedDate": None,
                "deliveryExpectedDelay": None,
                "discountAmount": None,
                "otaPackageType": None,
                "otaDestinationCountry": None,
                "bookingReference": None,
                "orderExtended": None,
                "orderOTA": None,
            },
            "media": "Computer",
            "numberOfAttempt": None,
            "contractNumber": "1234567",
            "buyer": {
                "title": None,
                "lastName": "Administrateur",
                "firstName": "Compte",
                "email": "admin@example.com",
                "shippingAdress": {
                    "title": None,
                    "name": None,
                    "firstName": None,
                    "lastName": None,
                    "street1": None,
                    "street2": None,
                    "streetNumber": None,
                    "cityName": None,
                    "zipCode": None,
                    "country": None,
                    "phone": None,
                    "state": None,
                    "county": None,
                    "phoneType": None,
                    "addressCreateDate": None,
                    "email": None,
                },
                "billingAddress": {
                    "title": None,
                    "name": None,
                    "firstName": None,
                    "lastName": None,
                    "street1": None,
                    "street2": None,
                    "streetNumber": None,
                    "cityName": None,
                    "zipCode": None,
                    "country": None,
                    "phone": None,
                    "state": None,
                    "county": None,
                    "phoneType": None,
                    "addressCreateDate": None,
                    "email": None,
                },
                "accountCreateDate": None,
                "accountAverageAmount": None,
                "accountOrderCount": None,
                "walletId": None,
                "walletDisplayed": None,
                "walletSecured": None,
                "walletCardInd": None,
                "ip": "92.132.197.116",
                "mobilePhone": None,
                "customerId": None,
                "legalStatus": None,
                "legalDocument": None,
                "birthDate": None,
                "fingerprintID": None,
                "deviceFingerprint": None,
                "isBot": None,
                "isIncognito": None,
                "isBehindProxy": None,
                "isFromTor": None,
                "isEmulator": None,
                "isRooted": None,
                "hasTimezoneMismatch": None,
                "loyaltyMemberType": None,
                "buyerExtended": None,
            },
            "linkedTransactionId": "000001100869915",
        }

    # pylint: enable=invalid-name


@pytest.fixture
def payline_monkeypatch(app, monkeypatch):
    """Fix methods to avoid external dependencies"""
    monkeypatch.setattr(
        "collectives.utils.payline.api._create_client",
        lambda wsdl_path: FakeSoapClient(),
    )
