"""Module to test payment module."""

# pylint: disable=unused-argument
from datetime import timedelta

from flask import url_for

from collectives.models import (
    Configuration,
    Payment,
    PaymentStatus,
    PaymentType,
    RegistrationStatus,
    db,
)
from collectives.utils.payment_provider import payline
from tests import utils
from tests.fixtures.client import login


def test_list_prices(leader_client, event1, enable_payment):
    """Test access to prices list"""
    response = leader_client.get(f"/payment/event/{event1.id}/edit_prices")
    assert response.status_code == 200


def test_list_prices_wrong_user(user1_client, event1):
    """Test refusal of price list to a regular user."""
    response = user1_client.get(f"/payment/event/{event1.id}/edit_prices")
    assert response.status_code == 302


def test_price_creation(leader_client, event1, enable_payment):
    """Test basic price and item creation."""
    event1.leaders.append(leader_client.user)
    db.session.add(event1)
    db.session.commit()
    response = leader_client.get(
        f"/payment/event/{event1.id}/edit_prices", follow_redirects=True
    )
    assert response.status_code == 200

    data = utils.load_data_from_form(response.text, "new_price")

    data["item_title"] = "Banana"
    data["title"] = "Adult"
    data["amount"] = 10
    data["enabled"] = "y"

    response = leader_client.post(
        f"/payment/event/{event1.id}/edit_prices", data=data, follow_redirects=True
    )
    assert response.status_code == 200
    prices = [len(i.prices) for i in event1.payment_items]
    assert len(prices) == 1

    price = event1.payment_items[0].prices[0]
    assert price.title == "Adult"
    assert price.item.title == "Banana"
    assert price.amount == 10
    assert price.enabled


def test_price_list(user1_client, paying_event, disabled_paying_event):
    """Test display of a paying event"""
    response = user1_client.get(
        f"/collectives/{paying_event.id}", follow_redirects=True
    )
    assert response.status_code == 200

    response = user1_client.get(
        f"/collectives/{disabled_paying_event.id}", follow_redirects=True
    )
    assert response.status_code == 200


def test_paying_free_registration(user1_client, free_paying_event, enable_payment):
    """Test a user registering to a free event."""
    response = user1_client.get(
        f"/collectives/{free_paying_event.id}", follow_redirects=True
    )
    assert response.status_code == 200

    data = utils.load_data_from_form(response.text, "select_payment_item")
    item = free_paying_event.payment_items[0]
    data["item_price"] = item.cheapest_price_for_user_now(user1_client.user).id

    response = user1_client.post(
        f"/collectives/{free_paying_event.id}/self_register",
        data=data,
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert len(free_paying_event.registrations) == 1
    assert free_paying_event.registrations[0].user == user1_client.user
    assert free_paying_event.registrations[0].status == RegistrationStatus.Active


def test_payline_registration(user1_client, paying_event, payline_monkeypatch):
    """Test a user registering to a paying event using payline"""
    response = user1_client.get(
        f"/collectives/{paying_event.id}", follow_redirects=True
    )
    assert response.status_code == 200

    data = utils.load_data_from_form(response.text, "select_payment_item")
    item = paying_event.payment_items[0]
    item_price = item.cheapest_price_for_user_now(user1_client.user)
    data["item_price"] = item_price.id

    assert item_price.amount > 0.0

    response = user1_client.post(
        f"/collectives/{paying_event.id}/self_register", data=data
    )
    assert response.status_code == 302
    response = user1_client.get(response.location, data=data)
    assert response.status_code == 302
    assert len(paying_event.registrations) == 1
    assert (
        response.location
        == "https://homologation-webpayment.payline.com/v2/?token=1jom6TVNaLuHygEB62681665928911817"
    )
    assert paying_event.registrations[0].user == user1_client.user
    assert paying_event.registrations[0].status == RegistrationStatus.PaymentPending

    # Check my_payments API for initiated payments
    response = user1_client.get("/api/payments/my/Initiated")
    assert response.status_code == 200
    api_data = response.json
    assert len(api_data) == 1
    assert api_data[0]["item"]["event"]["title"] == paying_event.title

    # Check my_payments API for completed payments (should be empty)
    response = user1_client.get("/api/payments/my/Approved")
    assert response.status_code == 200
    assert len(response.json) == 0

    # payline validation
    response = user1_client.post(
        "/payment/process?paylinetoken=1jom6TVNaLuHygEB62681665928911817", data=data
    )
    assert response.status_code == 302
    assert response.location == f"/collectives/{paying_event.id}-"
    assert paying_event.registrations[0].user == user1_client.user
    assert paying_event.registrations[0].status == RegistrationStatus.Active

    # Check my_payments API for initiated payments (should be empty now)
    response = user1_client.get("/api/payments/my/Initiated")
    assert response.status_code == 200
    assert len(response.json) == 0

    # Check my_payments API for completed payments
    response = user1_client.get("/api/payments/my/Approved")
    assert response.status_code == 200
    api_data = response.json
    assert len(api_data) == 1
    assert api_data[0]["item"]["event"]["title"] == paying_event.title


def test_helloasso_registration(user1_client, paying_event, helloasso_monkeypatch):
    """Test a user registering to a paying event using HelloAsso, once it is
    selected as the active payment provider"""
    response = user1_client.get(
        f"/collectives/{paying_event.id}", follow_redirects=True
    )
    assert response.status_code == 200

    data = utils.load_data_from_form(response.text, "select_payment_item")
    item = paying_event.payment_items[0]
    item_price = item.cheapest_price_for_user_now(user1_client.user)
    data["item_price"] = item_price.id

    assert item_price.amount > 0.0

    response = user1_client.post(
        f"/collectives/{paying_event.id}/self_register", data=data
    )
    assert response.status_code == 302
    response = user1_client.get(response.location, data=data)
    assert response.status_code == 302
    assert len(paying_event.registrations) == 1
    assert response.location == "https://checkout.helloasso-sandbox.com/987654"
    assert paying_event.registrations[0].user == user1_client.user
    assert paying_event.registrations[0].status == RegistrationStatus.PaymentPending

    payment = Payment.query.filter_by(
        registration=paying_event.registrations[0]
    ).first()
    assert payment.payment_type == PaymentType.HelloAsso

    # HelloAsso return callback (own token, embedded in the return URL)
    response = user1_client.post(
        f"/payment/process?token={payment.processor_token}", data=data
    )
    assert response.status_code == 302
    assert response.location == f"/collectives/{paying_event.id}-"
    assert paying_event.registrations[0].user == user1_client.user
    assert paying_event.registrations[0].status == RegistrationStatus.Active

    # Real (non-mock) payment: receipt carries no mock warning
    assert not payment.is_mock()
    response = user1_client.get(f"/payment/{payment.id}/receipt")
    assert response.status_code == 200
    assert "Paiement fictif" not in response.text


def test_helloasso_mock_registration(user1_client, paying_event, helloasso_monkeypatch):
    """Test that a payment made while HelloAsso is not configured (mock mode)
    is flagged as mock, with a warning on its receipt"""
    Configuration.get_item("HELLOASSO_CLIENT_ID").content = ""
    Configuration.uncache("HELLOASSO_CLIENT_ID")

    response = user1_client.get(
        f"/collectives/{paying_event.id}", follow_redirects=True
    )
    data = utils.load_data_from_form(response.text, "select_payment_item")
    item_price = paying_event.payment_items[0].cheapest_price_for_user_now(
        user1_client.user
    )
    data["item_price"] = item_price.id

    response = user1_client.post(
        f"/collectives/{paying_event.id}/self_register", data=data
    )
    response = user1_client.get(response.location)
    payment = Payment.query.one()
    assert response.location == f"/payment/do_mock_payment/{payment.processor_token}"
    assert payment.is_mock()

    # Mock "Paiement accepté" link
    amount = int(payment.amount_charged * 100)
    response = user1_client.get(
        f"/payment/process?token={payment.processor_token}"
        f"&message=ACCEPTED&amount={amount}"
    )
    assert response.status_code == 302
    assert paying_event.registrations[0].status == RegistrationStatus.Active

    response = user1_client.get(f"/payment/{payment.id}/receipt")
    assert response.status_code == 200
    assert "Paiement fictif" in response.text


def _start_helloasso_payment(client, event):
    """Self-registers the client's user to a paying event, up to the redirection
    to the HelloAsso checkout

    :return: The response redirecting to HelloAsso, and the created payment"""
    response = client.get(f"/collectives/{event.id}", follow_redirects=True)
    data = utils.load_data_from_form(response.text, "select_payment_item")
    item_price = event.payment_items[0].cheapest_price_for_user_now(client.user)
    data["item_price"] = item_price.id

    response = client.post(f"/collectives/{event.id}/self_register", data=data)
    response = client.get(response.location)
    return response, Payment.query.one()


def test_helloasso_expired_checkout(user1_client, paying_event, helloasso_checkouts):
    """Test that an unpaid HelloAsso checkout is replaced by a new one once it
    has expired, rather than sending the buyer back to its dead redirect URL"""
    response, payment = _start_helloasso_payment(user1_client, paying_event)
    assert response.location == "https://checkout.helloasso-sandbox.com/987654"
    first_token = payment.processor_token

    # Buyer leaves the checkout through HelloAsso's back link: still unpaid
    response = user1_client.get(f"/payment/cancel?token={first_token}")
    assert response.status_code == 302
    assert payment.status == PaymentStatus.Initiated
    assert paying_event.registrations[0].status == RegistrationStatus.PaymentPending

    # Before expiry, buyer is sent back to the same checkout
    response = user1_client.get(f"/payment/{payment.id}/pay")
    assert response.location == "https://checkout.helloasso-sandbox.com/987654"

    # After expiry (checkout page answers 404), a new checkout is created
    helloasso_checkouts.expired.add(987654)
    response = user1_client.get(f"/payment/{payment.id}/pay")
    assert response.location == "https://checkout.helloasso-sandbox.com/987655"
    assert payment.processor_token != first_token
    assert payment.status == PaymentStatus.Initiated

    # Paying the new checkout confirms the registration
    helloasso_checkouts.payment_states[987655] = "Authorized"
    response = user1_client.get(f"/payment/process?token={payment.processor_token}")
    assert response.status_code == 302
    assert payment.status == PaymentStatus.Approved
    assert paying_event.registrations[0].status == RegistrationStatus.Active


def test_helloasso_expired_checkout_with_order(
    user1_client, paying_event, helloasso_checkouts
):
    """Test that a checkout is never replaced once HelloAsso has an order for
    it, so that a payment still in progress cannot be made twice"""
    response, payment = _start_helloasso_payment(user1_client, paying_event)
    helloasso_checkouts.payment_states[987654] = "WaitingAuthentication"

    helloasso_checkouts.expired.add(987654)
    response = user1_client.get(f"/payment/{payment.id}/pay")
    assert response.location == "https://checkout.helloasso-sandbox.com/987654"
    assert payment.status == PaymentStatus.Initiated


def test_payline_registration_unfinalized(
    user1_client, paying_event, payline_monkeypatch
):
    """Test a user registering to a paying event using payline, without receiving finalization callback"""
    response = user1_client.get(
        f"/collectives/{paying_event.id}", follow_redirects=True
    )
    assert response.status_code == 200

    data = utils.load_data_from_form(response.text, "select_payment_item")
    item = paying_event.payment_items[0]
    item_price = item.cheapest_price_for_user_now(user1_client.user)
    data["item_price"] = item_price.id

    assert item_price.amount > 0.0

    response = user1_client.post(
        f"/collectives/{paying_event.id}/self_register", data=data
    )
    assert response.status_code == 302
    response = user1_client.get(response.location, data=data)
    assert response.status_code == 302
    assert len(paying_event.registrations) == 1
    assert (
        response.location
        == "https://homologation-webpayment.payline.com/v2/?token=1jom6TVNaLuHygEB62681665928911817"
    )
    assert paying_event.registrations[0].user == user1_client.user
    assert paying_event.registrations[0].status == RegistrationStatus.PaymentPending

    # Check my_payments API for initiated payments
    response = user1_client.get("/api/payments/my/Initiated")
    assert response.status_code == 200
    api_data = response.json
    assert len(api_data) == 1
    assert api_data[0]["item"]["event"]["title"] == paying_event.title

    # Check my_payments API for completed payments (should be empty)
    response = user1_client.get("/api/payments/my/Approved")
    assert response.status_code == 200
    assert len(response.json) == 0

    # Re-access payment page. Should update status from payline API
    response = user1_client.get(
        url_for("payment.request_payment", payment_id=api_data[0]["id"])
    )
    assert response.status_code == 302
    assert response.location == f"/collectives/{paying_event.id}-"
    assert paying_event.registrations[0].user == user1_client.user
    assert paying_event.registrations[0].status == RegistrationStatus.Active

    # Check my_payments API for initiated payments (should be empty now)
    response = user1_client.get("/api/payments/my/Initiated")
    assert response.status_code == 200
    assert len(response.json) == 0

    # Check my_payments API for completed payments
    response = user1_client.get("/api/payments/my/Approved")
    assert response.status_code == 200
    api_data = response.json
    assert len(api_data) == 1
    assert api_data[0]["item"]["event"]["title"] == paying_event.title


def _initiate_payline_payment(client, event):
    """Registers the client user to a paying event, up to the Payline page

    :return: The payment, still in progress
    """
    response = client.get(f"/collectives/{event.id}", follow_redirects=True)
    data = utils.load_data_from_form(response.text, "select_payment_item")
    item = event.payment_items[0]
    data["item_price"] = item.cheapest_price_for_user_now(client.user).id
    response = client.post(f"/collectives/{event.id}/self_register", data=data)
    response = client.get(response.location)
    assert response.status_code == 302
    assert event.registrations[0].status == RegistrationStatus.PaymentPending
    return event.registrations[0].payments[0]


def _set_payline_status(monkeypatch, short_message, code="00000"):
    """Makes Payline answer with the given status for any payment"""
    get_details = payline.api.get_web_payment_details

    def get_details_with_status(token):
        details = get_details(token)
        details.result.short_message = short_message
        details.result.code = code
        return details

    monkeypatch.setattr(payline.api, "get_web_payment_details", get_details_with_status)


def _check_stale_payment(app, client, admin_user, payment):
    """Ages the payment, then checks it as an accountant

    :return: The listing page after the check
    """
    payment.creation_time -= timedelta(hours=2)
    db.session.commit()
    login(client, admin_user, app.config["ADMINPWD"])
    response = client.post(f"/payment/{payment.id}/check")
    assert response.status_code == 302
    assert response.location == "/payment/pending"
    return client.get(response.location)


def test_pending_payments(
    app, user1_client, admin_user, paying_event, payline_monkeypatch, monkeypatch
):
    """Test that an accountant may check a payment Payline did not notify"""
    payment = _initiate_payline_payment(user1_client, paying_event)

    # Only accountants may list pending payments
    response = user1_client.get("/payment/pending")
    assert response.status_code == 302
    response = user1_client.post(f"/payment/{payment.id}/check")
    assert response.status_code == 302
    assert payment.status == PaymentStatus.Initiated

    client = user1_client
    login(client, admin_user, app.config["ADMINPWD"])

    # Recent payments are not listed
    payment.creation_time -= timedelta(minutes=50)
    db.session.commit()
    response = client.get("/payment/pending")
    assert response.status_code == 200
    assert f"/payment/{payment.id}/check" not in response.text

    payment.creation_time -= timedelta(minutes=20)
    db.session.commit()
    response = client.get("/payment/pending")
    assert f"/payment/{payment.id}/check" in response.text

    # Payments never sent to Payline are not listed
    token = payment.processor_token
    payment.processor_token = ""
    db.session.commit()
    response = client.get("/payment/pending")
    assert f"/payment/{payment.id}/check" not in response.text
    payment.processor_token = token
    db.session.commit()

    # Payline does not answer: the payment stays in progress
    get_details = payline.api.get_web_payment_details
    monkeypatch.setattr(payline.api, "get_web_payment_details", lambda token: None)
    response = client.post(f"/payment/{payment.id}/check")
    assert response.status_code == 302
    assert response.location == "/payment/pending"
    payment = db.session.get(Payment, payment.id)
    assert payment.status == PaymentStatus.Initiated

    # Payline accepted the payment
    monkeypatch.setattr(payline.api, "get_web_payment_details", get_details)
    response = client.post(f"/payment/{payment.id}/check")
    assert response.status_code == 302
    payment = db.session.get(Payment, payment.id)
    assert payment.status == PaymentStatus.Approved
    assert payment.registration.status == RegistrationStatus.Active

    response = client.get(response.location)
    assert "mis à jour d&#39;après Payline : Approuvé" in response.text
    assert f"/payment/{payment.id}/check" not in response.text

    # Checking it again does not change anything
    response = client.post(f"/payment/{payment.id}/check", follow_redirects=True)
    assert "est déjà finalisé : Approuvé" in response.text


def test_pending_payment_refused(
    app, user1_client, admin_user, paying_event, payline_monkeypatch, monkeypatch
):
    """Test that a refused payment deletes the registration pending payment"""
    payment = _initiate_payline_payment(user1_client, paying_event)
    _set_payline_status(monkeypatch, "REFUSED")

    response = _check_stale_payment(app, user1_client, admin_user, payment)
    assert "mis à jour d&#39;après Payline : Refusé" in response.text
    assert "a été supprimée" in response.text
    payment = db.session.get(Payment, payment.id)
    assert payment.status == PaymentStatus.Refused
    assert len(paying_event.registrations) == 0


def test_pending_payment_expired_after_settlement(
    app, user1_client, admin_user, paying_event, payline_monkeypatch, monkeypatch
):
    """Test that an expired payment keeps a registration settled meanwhile"""
    payment = _initiate_payline_payment(user1_client, paying_event)
    registration = payment.registration
    registration.status = RegistrationStatus.Active
    db.session.commit()
    _set_payline_status(monkeypatch, "REFUSED", "02324")

    _check_stale_payment(app, user1_client, admin_user, payment)
    payment = db.session.get(Payment, payment.id)
    assert payment.status == PaymentStatus.Expired
    assert payment.registration.status == RegistrationStatus.Active


def test_pending_payment_accepted_after_rejection(
    app, user1_client, admin_user, paying_event, payline_monkeypatch
):
    """Test that an accepted payment does not revive a rejected registration"""
    payment = _initiate_payline_payment(user1_client, paying_event)
    registration = payment.registration
    registration.status = RegistrationStatus.Rejected
    db.session.commit()

    response = _check_stale_payment(app, user1_client, admin_user, payment)
    assert "un remboursement est peut-être nécessaire" in response.text
    payment = db.session.get(Payment, payment.id)
    assert payment.status == PaymentStatus.Approved
    assert payment.registration.status == RegistrationStatus.Rejected


def test_pending_helloasso_payments(
    app, user1_client, admin_user, paying_event, helloasso_checkouts
):
    """Test that an accountant may check HelloAsso payments, including
    abandoned ones, which HelloAsso never reports as expired"""
    _, payment = _start_helloasso_payment(user1_client, paying_event)
    payment.creation_time -= timedelta(hours=2)
    db.session.commit()
    login(user1_client, admin_user, app.config["ADMINPWD"])

    response = user1_client.get("/payment/pending")
    assert f"/payment/{payment.id}/check" in response.text
    assert "HelloAsso" in response.text

    # Checkout page still valid: the buyer may still pay
    response = user1_client.post(f"/payment/{payment.id}/check", follow_redirects=True)
    assert (
        f"HelloAsso indique que le paiement n°{payment.id} est toujours"
        in response.text
    )
    assert payment.status == PaymentStatus.Initiated

    # A payment in progress on an expired checkout page is kept as is
    helloasso_checkouts.expired.add(987654)
    helloasso_checkouts.payment_states[987654] = "WaitingAuthentication"
    user1_client.post(f"/payment/{payment.id}/check")
    payment = db.session.get(Payment, payment.id)
    assert payment.status == PaymentStatus.Initiated

    # An expired checkout page without payment cannot be paid anymore
    del helloasso_checkouts.payment_states[987654]
    response = user1_client.post(f"/payment/{payment.id}/check", follow_redirects=True)
    assert "mis à jour d&#39;après HelloAsso : Inabouti" in response.text
    assert "a été supprimée" in response.text
    payment = db.session.get(Payment, payment.id)
    assert payment.status == PaymentStatus.Expired
    assert len(paying_event.registrations) == 0


def test_pending_helloasso_payment_accepted(
    app, user1_client, admin_user, paying_event, helloasso_checkouts
):
    """Test that an accountant may finalize a HelloAsso payment paid without
    notification"""
    _, payment = _start_helloasso_payment(user1_client, paying_event)
    helloasso_checkouts.payment_states[987654] = "Authorized"

    response = _check_stale_payment(app, user1_client, admin_user, payment)
    assert "mis à jour d&#39;après HelloAsso : Approuvé" in response.text
    payment = db.session.get(Payment, payment.id)
    assert payment.status == PaymentStatus.Approved
    assert payment.registration.status == RegistrationStatus.Active
