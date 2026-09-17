"""Tests that the mock Payline API is only available in debug/testing mode (audit M5)."""

import pytest

from collectives.models import Configuration, db
from collectives.utils import payline


@pytest.fixture
def unconfigured_payline(app):
    """Leave Payline unconfigured (empty merchant id) so that the mock API is selected."""
    item = Configuration.get_item("PAYLINE_MERCHANT_ID")
    item.content = ""
    db.session.add(item)
    db.session.commit()
    Configuration.uncache("PAYLINE_MERCHANT_ID")
    payline.api.reload_config()
    yield
    # Do not leak state to other tests
    payline.api.payline_merchant_id = None
    payline.api._webpayment_client = None  # pylint: disable=protected-access
    payline.api._directpayment_client = None  # pylint: disable=protected-access


def test_payline_mock_disabled_outside_debug_and_testing(app, unconfigured_payline):
    """Outside debug/testing, an unconfigured Payline API returns no result."""
    query = "paylinetoken=x&message=ACCEPTED&amount=100"
    with app.test_request_context(f"/payment/process?{query}"):
        assert payline.api.disabled()
        assert payline.api.mock_allowed()
        details = payline.api.get_web_payment_details("x")
        assert details is not None
        assert details.amount() == 1

        app.testing = False
        try:
            assert not payline.api.mock_allowed()
            assert payline.api.get_web_payment_details("x") is None
            assert payline.api.do_web_payment(None, None) is None
            assert payline.api.do_refund(None) is None
        finally:
            app.testing = True


def test_mock_payment_page_hidden_outside_debug_and_testing(
    app, client, unconfigured_payline
):
    """The mock payment page is not served outside debug/testing."""
    item = Configuration.get_item("PAYMENTS_ENABLED")
    item.content = True
    db.session.add(item)
    db.session.commit()
    Configuration.uncache("PAYMENTS_ENABLED")

    app.testing = False
    try:
        response = client.get("/payment/do_mock_payment/some-token")
        # The application turns 404 into a redirection to the event index
        assert response.status_code in (302, 404)
        if response.status_code == 302:
            assert response.headers["Location"].endswith("/collectives/")
    finally:
        app.testing = True
