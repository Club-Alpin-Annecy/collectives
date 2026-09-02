"""Mock functions for HelloAsso."""

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
                "state": "Authorized",
                "order": {
                    "amount": {"total": 1000},
                    "payments": [{"id": "555"}],
                },
            }
        )
    raise ValueError(f"Unexpected GET url in HelloAsso mock: {url}")


_CONFIG_KEYS = (
    "PAYMENT_ENABLED",
    "HELLOASSO_CLIENT_ID",
    "HELLOASSO_CLIENT_SECRET",
    "HELLOASSO_ORGANIZATION_SLUG",
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
