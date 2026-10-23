"""Mock functions for HelloAsso."""

import itertools
from types import SimpleNamespace

import pytest

from collectives.models import Configuration

# pylint: disable=unused-argument


class FakeResponse:
    """Fake requests.Response used to mock the HelloAsso REST API."""

    def __init__(self, json_data):
        """Constructor"""
        self._json_data = json_data

    def raise_for_status(self):
        """No-op: the mock never returns an HTTP error status"""

    def json(self):
        """:return: the mocked JSON payload"""
        return self._json_data


def fake_post(url, **kwargs):
    """Mock POST calls to the HelloAsso API"""
    if url.endswith("/oauth2/token"):
        return FakeResponse({"access_token": "fake-access-token", "expires_in": 1800})
    if url.endswith("/checkout-intents"):
        return FakeResponse(
            {
                "id": 987654,
                "redirectUrl": "https://checkout.helloasso-sandbox.com/987654",
            }
        )
    if url.endswith("/refund"):
        return FakeResponse({"state": "Refunded"})
    raise ValueError(f"Unexpected POST url in HelloAsso mock: {url}")


def fake_get(url, **kwargs):
    """Mock GET calls to the HelloAsso API"""
    if "/checkout-intents/" in url:
        return FakeResponse(
            {
                "id": "987654",
                "order": {
                    "amount": {"total": 1000},
                    "payments": [{"id": "555", "state": "Authorized"}],
                },
            }
        )
    raise ValueError(f"Unexpected GET url in HelloAsso mock: {url}")


_CONFIG_KEYS = (
    "PAYMENT_ENABLED",
    "HELLOASSO_CLIENT_ID",
    "HELLOASSO_CLIENT_SECRET",
    "HELLOASSO_ORGANIZATION_SLUG",
    "HELLOASSO_SANDBOX",
)


@pytest.fixture
def helloasso_monkeypatch(app, monkeypatch):
    """Fix methods and configuration to avoid external dependencies"""
    monkeypatch.setattr(
        "collectives.utils.payment_provider.helloasso.requests.post", fake_post
    )
    monkeypatch.setattr(
        "collectives.utils.payment_provider.helloasso.requests.get", fake_get
    )

    Configuration.get_item("PAYMENT_ENABLED").content = "HelloAsso"
    Configuration.get_item("HELLOASSO_CLIENT_ID").content = "test-client-id"
    Configuration.get_item("HELLOASSO_CLIENT_SECRET").content = "test-secret"
    Configuration.get_item("HELLOASSO_ORGANIZATION_SLUG").content = "test-org"
    for name in _CONFIG_KEYS:
        Configuration.uncache(name)

    yield

    # Configuration._cache is a process-wide dict, not scoped to this test's
    # app/db: invalidate it again on teardown so the next test (running
    # against its own fresh db) does not read back these stale cached values.
    for name in _CONFIG_KEYS:
        Configuration.uncache(name)


@pytest.fixture
def helloasso_checkouts(helloasso_monkeypatch, monkeypatch):
    """Mock creating a new checkout intent (id 987654, then 987655, ...) on
    each checkout request.

    :return: An object whose ``payment_states`` dict maps a checkout intent
        id to the state of its payment (e.g. ``{987654: "Authorized"}``; no
        order, i.e. nothing paid, if absent), and whose ``expired`` set lists
        the checkout intents whose checkout page answers 404."""
    checkouts = SimpleNamespace(payment_states={}, expired=set())
    intent_ids = itertools.count(987654)

    def checkouts_post(url, **kwargs):
        """Mock POST calls, creating a new checkout intent on each request"""
        if url.endswith("/checkout-intents"):
            intent_id = next(intent_ids)
            return FakeResponse(
                {
                    "id": intent_id,
                    "redirectUrl": f"https://checkout.helloasso-sandbox.com/{intent_id}",
                }
            )
        return fake_post(url, **kwargs)

    def checkouts_get(url, **kwargs):
        """Mock GET calls to a checkout intent, or to its checkout page,
        according to the state recorded in ``checkouts``"""
        intent_id = int(url.rsplit("/", 1)[-1])
        if "/checkout-intents/" not in url:
            # Checkout page the buyer is redirected to
            expired = intent_id in checkouts.expired
            return SimpleNamespace(status_code=404 if expired else 200)

        data = {"id": intent_id}
        if intent_id in checkouts.payment_states:
            state = checkouts.payment_states[intent_id]
            data["order"] = {
                "amount": {"total": 1000},
                "payments": [{"id": "555", "state": state}],
            }
        return FakeResponse(data)

    monkeypatch.setattr(
        "collectives.utils.payment_provider.helloasso.requests.post", checkouts_post
    )
    monkeypatch.setattr(
        "collectives.utils.payment_provider.helloasso.requests.get", checkouts_get
    )
    return checkouts
