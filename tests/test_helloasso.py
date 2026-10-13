"""Module to test the HelloAsso payment provider."""

# pylint: disable=unused-argument
import json
from types import SimpleNamespace

import pytest
import requests

from collectives.models import Configuration
from collectives.utils.payment_provider import helloasso
from tests.mock import helloasso as helloasso_mock

PAYMENT = SimpleNamespace(id=1, raw_metadata=json.dumps({"id": 987654}))
""" Minimal stand-in for a payment already submitted to HelloAsso """


class UnauthorizedResponse(helloasso_mock.FakeResponse):
    """Fake response for a request whose access token has been rejected"""

    status_code = 401
    text = "Unauthorized"

    def __init__(self):
        """Constructor"""
        super().__init__({})

    def raise_for_status(self):
        """Raises the same error as requests does for a 401"""
        raise requests.HTTPError("401 Unauthorized", response=self)


@pytest.fixture
def token_requests(helloasso_monkeypatch, monkeypatch):
    """Records the URL of every OAuth2 token request made to HelloAsso"""
    urls = []

    def recording_post(url, **kwargs):
        """Mock POST calls, recording OAuth2 token requests"""
        if url.endswith("/oauth2/token"):
            urls.append(url)
        return helloasso_mock.fake_post(url, **kwargs)

    monkeypatch.setattr(
        "collectives.utils.payment_provider.helloasso.requests.post", recording_post
    )
    return urls


@pytest.mark.parametrize(
    "name,value",
    [
        ("HELLOASSO_SANDBOX", True),
        ("HELLOASSO_CLIENT_ID", "other-client-id"),
        ("HELLOASSO_CLIENT_SECRET", "other-secret"),
        ("HELLOASSO_ORGANIZATION_SLUG", "other-org"),
    ],
)
def test_token_reset_on_config_change(token_requests, name, value):
    """Test that the cached access token is dropped when any setting it
    depends on changes"""
    assert helloasso.api.retrieve_remote_payment_status(PAYMENT) is not None
    count = len(token_requests)

    # Token is cached while the configuration is unchanged
    assert helloasso.api.retrieve_remote_payment_status(PAYMENT) is not None
    assert len(token_requests) == count

    Configuration.get_item(name).content = value
    Configuration.uncache(name)

    assert helloasso.api.retrieve_remote_payment_status(PAYMENT) is not None
    assert len(token_requests) == count + 1
    if name == "HELLOASSO_SANDBOX":
        assert token_requests[-1].startswith(helloasso.SANDBOX_API_BASE)


def test_token_reset_on_unauthorized(token_requests, monkeypatch):
    """Test that the cached access token is dropped when HelloAsso rejects it"""
    assert helloasso.api.retrieve_remote_payment_status(PAYMENT) is not None
    count = len(token_requests)

    monkeypatch.setattr(
        "collectives.utils.payment_provider.helloasso.requests.get",
        lambda url, **kwargs: UnauthorizedResponse(),
    )
    assert helloasso.api.retrieve_remote_payment_status(PAYMENT) is None
    assert len(token_requests) == count

    monkeypatch.setattr(
        "collectives.utils.payment_provider.helloasso.requests.get",
        helloasso_mock.fake_get,
    )
    assert helloasso.api.retrieve_remote_payment_status(PAYMENT) is not None
    assert len(token_requests) == count + 1
