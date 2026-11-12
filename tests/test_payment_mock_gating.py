"""Tests that the mock payment APIs are only available in debug/testing mode."""

# pylint: disable=unused-argument
import json
from types import SimpleNamespace

import pytest

from collectives.models import Configuration, Payment, db
from collectives.utils.payment_provider import helloasso, payline
from tests import utils

PROVIDER_ID_ITEMS = ("PAYLINE_MERCHANT_ID", "HELLOASSO_CLIENT_ID")
""" Configuration items whose emptiness puts a provider in mock mode """

PAYMENT = SimpleNamespace(
    id=1,
    processor_token="x",
    raw_metadata=json.dumps(
        {"result": {"code": "00000", "shortMessage": "ACCEPTED", "longMessage": ""}}
    ),
)
""" Minimal stand-in for a payment already submitted to a provider """

PROVIDERS = pytest.mark.parametrize(
    "provider", [payline.api, helloasso.api], ids=["payline", "helloasso"]
)


@pytest.fixture
def unconfigured_providers(app):
    """Leave Payline and HelloAsso unconfigured so that their mock APIs are selected."""
    # FLASK_DEBUG may be set in the developer environment
    app.debug = False
    for name in PROVIDER_ID_ITEMS:
        Configuration.get_item(name).content = ""
    db.session.commit()
    for name in PROVIDER_ID_ITEMS:
        Configuration.uncache(name)
    # The providers are process-wide singletons: drop the identifiers
    # that a previous test may have left in them
    payline.api.reload_config()
    helloasso.api.reload_config()
    yield
    # Do not leak state to other tests
    for name in PROVIDER_ID_ITEMS:
        Configuration.uncache(name)
    payline.api.payline_merchant_id = None
    payline.api._webpayment_client = None  # pylint: disable=protected-access
    payline.api._directpayment_client = None  # pylint: disable=protected-access


@PROVIDERS
def test_mock_disabled_outside_debug_and_testing(app, unconfigured_providers, provider):
    """Outside debug/testing, an unconfigured provider returns no result."""
    query = "paylinetoken=x&message=ACCEPTED&amount=100"
    with app.test_request_context(f"/payment/process?{query}"):
        assert provider.disabled()
        assert provider.mock_allowed()
        status = provider.retrieve_remote_payment_status(PAYMENT)
        assert status is not None
        assert status.amount == 1

        app.testing = False
        try:
            assert not provider.mock_allowed()
            assert provider.retrieve_remote_payment_status(PAYMENT) is None
            assert provider.do_refund(PAYMENT) is None
        finally:
            app.testing = True


def test_checkout_refused_outside_debug_and_testing(app, unconfigured_providers):
    """Outside debug/testing, no mock checkout is created."""
    with app.test_request_context("/"):
        app.testing = False
        try:
            assert payline.api.do_web_payment(None, None) is None
            assert helloasso.api.create_checkout(None, None) is None
        finally:
            app.testing = True


def test_mock_payment_page_hidden_outside_debug_and_testing(
    app, user1_client, paying_event, helloasso_monkeypatch
):
    """The mock payment page is not served outside debug/testing."""
    app.debug = False
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
    mock_url = f"/payment/do_mock_payment/{payment.processor_token}"
    assert response.location == mock_url
    assert user1_client.get(mock_url).status_code == 200

    app.testing = False
    try:
        response = user1_client.get(mock_url)
    finally:
        app.testing = True
    # The application turns 404 into a redirection to the event index
    assert response.status_code in (302, 404)
    if response.status_code == 302:
        assert response.headers["Location"].endswith("/collectives/")


def test_payline_mock_allowed_reloads_config(app, unconfigured_providers):
    """mock_allowed() reads the current merchant id, not a stale one."""
    item = Configuration.get_item("PAYLINE_MERCHANT_ID")
    item.content = "merchant"
    db.session.add(item)
    db.session.commit()
    Configuration.uncache("PAYLINE_MERCHANT_ID")
    # Simulate a fresh worker that never loaded the configuration
    payline.api.payline_merchant_id = ""

    with app.test_request_context("/"):
        assert not payline.api.mock_allowed()
