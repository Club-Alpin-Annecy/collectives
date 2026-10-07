"""Module to test the anonymized export of the database."""

# pylint: disable=unused-argument

import json
from datetime import date, datetime
from decimal import Decimal

import pytest
from flask import url_for
from sqlalchemy.engine import make_url

from collectives.models import (
    ActivityType,
    Configuration,
    ConfigurationItem,
    ConfirmationToken,
    ConfirmationTokenType,
    Payment,
    PaymentStatus,
    PaymentType,
    Retex,
    UploadedFile,
    User,
    db,
)
from collectives.utils.anonymize import anonymize, anonymize_database
from collectives.utils.payline import PaymentDetails


def _anonymize(password=None):
    """Run the anonymization on the test database, then reload the session."""
    db.session.commit()
    with db.engine.begin() as connection:
        anonymize(connection, password)
    db.session.expire_all()


def test_anonymize_users(user1: User, admin_user: User):
    """Personal data of users is replaced, statistical data is kept."""
    user1.date_of_birth = date(1985, 6, 15)
    user1.phone = "0612345678"
    user1.emergency_contact_name = "Jeanne Dupont"
    original = {
        "mail": user1.mail,
        "first_name": user1.first_name,
        "last_name": user1.last_name,
        "license": user1.license,
        "gender": user1.gender,
        "license_category": user1.license_category,
    }

    _anonymize(password="anonyme")

    assert user1.mail == f"user{user1.id}@example.org"
    assert user1.first_name == f"Prénom{user1.id}"
    assert user1.last_name == f"Nom{user1.id}"
    assert user1.license not in (original["license"], "")
    assert user1.date_of_birth == date(1985, 1, 1)
    assert user1.phone == "0600000000"
    assert user1.emergency_contact_name == "Contact d'urgence"
    assert user1.password == "anonyme"
    assert user1.gender == original["gender"]
    assert user1.license_category == original["license_category"]

    # The admin account keeps its mail, so that the application finds it.
    assert admin_user.mail == "admin"


def test_anonymize_without_password(user1: User):
    """Without a password, accounts cannot log in."""
    _anonymize()

    assert user1.password is None


def test_anonymize_secrets(app):
    """Hidden configuration items and third-party identifiers are emptied."""
    for name in ["SMTP_PASSWORD", "EXTRANET_ACCOUNT_ID", "PAYLINE_MERCHANT_NAME"]:
        ConfigurationItem.query.filter_by(name=name).one().content = "secret"

    _anonymize()

    def content(name):
        item = ConfigurationItem.query.filter_by(name=name).one()
        return json.loads(item.json_content)

    assert content("SMTP_PASSWORD") == ""
    assert content("EXTRANET_ACCOUNT_ID") == ""
    assert content("PAYLINE_MERCHANT_NAME") == "secret"


PAYLINE_RESPONSE = {
    "result": {
        "code": "00000",
        "shortMessage": "ACCEPTED",
        "longMessage": "Transaction approved",
    },
    "transaction": {"id": "26170164035912", "date": "16/10/2022 16:49:56"},
    "payment": {"amount": "1500", "currency": "978", "contractNumber": "1234567"},
    "card": {"number": "497010XXXXXX1234", "cardholder": "Jeanne Dupont"},
    "buyer": {"lastName": "Dupont", "email": "jeanne.dupont@gmail.com"},
    "privateDataList": {"privateData": [{"key": "license", "value": "740120001234"}]},
}


def _online_payment(user, event):
    """An approved online payment, with a real-looking Payline response."""
    payment = Payment(buyer=user, item_price=event.payment_items[0].prices[0])
    payment.status = PaymentStatus.Approved
    payment.processor_token = "payline-token"
    payment.processor_order_ref = "CAF20221016ALP0042"
    payment.processor_url = "https://payline.example/session"
    payment.raw_metadata = json.dumps(PAYLINE_RESPONSE)
    db.session.add(payment)
    return payment


def test_anonymize_payments(user1: User, paying_event):
    """Buyer and card details are dropped; amount and order reference are kept."""
    online = _online_payment(user1, paying_event)
    cash = Payment(buyer=user1, item_price=paying_event.payment_items[0].prices[0])
    cash.payment_type = PaymentType.Cash
    cash.raw_metadata = "Chèque nº 1234 de Jeanne Dupont"
    db.session.add(cash)

    _anonymize()

    assert "Dupont" not in online.raw_metadata
    assert "1234567" not in online.raw_metadata
    assert "26170164035912" not in online.raw_metadata
    details = PaymentDetails.from_metadata(online.raw_metadata)
    assert details.result.is_accepted()
    assert details.amount() == Decimal("15")
    assert online.processor_order_ref == "CAF20221016ALP0042"
    assert online.processor_token == f"anon-{online.id}"
    assert online.processor_url is None
    assert cash.raw_metadata == ""


def test_refund_after_anonymization(admin_client, user1: User, paying_event):
    """Refunding an anonymized online payment goes through the mock Payline."""
    ConfigurationItem.query.filter_by(name="REFUND_ENABLED").one().content = True
    Configuration.uncache("REFUND_ENABLED")
    payment = _online_payment(user1, paying_event)

    _anonymize()

    response = admin_client.post(
        url_for("payment.refund_all", event_id=paying_event.id)
    )
    assert response.status_code == 302
    db.session.expire_all()
    assert payment.status == PaymentStatus.Refunded
    assert json.loads(payment.refund_metadata)["result"]["code"] == "00000"


def test_anonymize_free_texts(user1: User, event1_with_answers, past_event):
    """Tokens are deleted, answers and retex are scrubbed, event descriptions
    lose their phones and mails only."""
    token = ConfirmationToken(user1.license, user1)
    token.token_type = ConfirmationTokenType.ActivateAccount
    db.session.add(token)
    past_event.retex = Retex(
        author_id=past_event.leaders[0].id, description="Chute de Jeanne Dupont"
    )
    past_event.description = (
        "Départ 8h, 1 200 m de dénivelé. Contact : 06 12 34 56 78 "
        "ou jeanne.dupont@gmail.com"
    )
    past_event.rendered_description = '<a href="tel:+33612345678">appeler</a>'

    _anonymize()

    assert ConfirmationToken.query.count() == 0
    answer = event1_with_answers.questions[0].answers[0]
    assert answer.value == "[anonymisé]"
    assert past_event.retex.description == "[anonymisé]"
    assert past_event.description == (
        "Départ 8h, 1 200 m de dénivelé. Contact : 0600000000 ou contact@example.org"
    )
    assert past_event.rendered_description == '<a href="tel:0600000000">appeler</a>'


def test_anonymize_uploads(app, user1: User):
    """Original file names are replaced; date prefix and extension are kept."""
    upload = UploadedFile(
        name="certificat_dupont.pdf",
        path="22_10_16_certificat_dupont.pdf",
        date=datetime(2022, 10, 16),
        size=1,
        user_id=user1.id,
    )
    db.session.add(upload)

    _anonymize()

    assert upload.name == f"fichier-{upload.id}.pdf"
    assert upload.path == f"22_10_16_fichier-{upload.id}.pdf"


def test_anonymize_club_contacts(app):
    """Contact addresses of the club and of activities are replaced."""
    ConfigurationItem.query.filter_by(
        name="SECRETARIAT_EMAIL"
    ).one().content = "secretariat@cafannecy.fr"
    activity = ActivityType.query.first()
    activity.email = "alpinisme@cafannecy.fr"

    _anonymize()

    item = ConfigurationItem.query.filter_by(name="SECRETARIAT_EMAIL").one()
    assert json.loads(item.json_content) == "secretariat@example.org"
    assert activity.email == f"activite-{activity.id}@example.org"


def test_anonymize_database_refuses_non_temporary_database():
    """The anonymization never runs on a database not named as temporary."""
    with pytest.raises(ValueError):
        anonymize_database(make_url("mysql+pymysql://user:pwd@localhost/collectives"))
