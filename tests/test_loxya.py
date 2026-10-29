"""Module to test the Loxya API client."""

import pytest

from collectives.models import Configuration
from collectives.utils import loxya
from tests.mock.loxya import CONNECTION, set_loxya_connection, set_loxya_enabled

# pylint: disable=unused-argument,protected-access


def test_off_by_default(app):
    """Without LOXYA_ENABLED, the API is off even when fully configured.

    This is what keeps the integration out of the way of every other club.
    """
    set_loxya_connection()
    client = loxya.LoxyaApi()

    assert not loxya.feature_enabled()
    assert client.disabled()
    with pytest.raises(loxya.LoxyaError):
        client.get("/api/beneficiaries")


@pytest.mark.parametrize("missing", sorted(CONNECTION))
def test_enabled_but_incomplete_stays_off(app, missing):
    """Switched on, but a connection setting is still to be entered: no call.

    The integration shows — technicians must see where to enter it — but the API
    stays off.
    """
    set_loxya_enabled()
    set_loxya_connection(**{missing: ""})

    assert loxya.feature_enabled()
    assert loxya.missing_settings() == [missing]
    assert loxya.LoxyaApi().disabled()


def test_reauthenticates_once_on_401(loxya_session):
    """An expired token is renewed and the request replayed, not lost."""
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", 200, {"id": 1})
    loxya_session.token_valid = False

    assert client.get("/api/beneficiaries/1") == {"id": 1}
    assert loxya_session.auth_count == 2


@pytest.mark.parametrize(
    "status_code,expected",
    [
        (404, loxya.LoxyaNotFoundError),
        (500, loxya.LoxyaError),
    ],
)
def test_status_codes_map_to_exceptions(loxya_session, status_code, expected):
    """A 404 — also a beneficiary in the trash bin — has its own exception."""
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", status_code, {})

    with pytest.raises(expected):
        client.get("/api/beneficiaries/1")


def test_timeout_is_always_set(loxya_session):
    """No call may hang: an unresponsive Loxya must not freeze a worker. The
    timeout is read from the hot configuration at each call."""
    Configuration.get_item("LOXYA_TIMEOUT").content = 3
    Configuration.uncache("LOXYA_TIMEOUT")
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", 200, {"id": 1})

    client.get("/api/beneficiaries/1")

    _, _, kwargs = loxya_session.calls[0]
    assert kwargs["timeout"] == 3
