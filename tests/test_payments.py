"""Module to test payment module."""

# pylint: disable=unused-argument

from collectives.models import RegistrationStatus, db
from tests import utils


def test_list_prices(leader_client, event1):
    """Test access to prices list"""
    response = leader_client.get(f"/payment/event/{event1.id}/edit_prices")
    assert response.status_code == 200


def test_list_prices_wrong_user(user1_client, event1):
    """Test refusal of price list to a regular user."""
    response = user1_client.get(f"/payment/event/{event1.id}/edit_prices")
    assert response.status_code == 302


def test_price_creation(leader_client, event1):
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


def test_paying_free_registration(user1_client, free_paying_event):
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
