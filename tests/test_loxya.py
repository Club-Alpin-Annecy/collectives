"""Module to test the Loxya API client."""

from datetime import datetime, timedelta

import pytest

from collectives.utils import loxya
from tests.mock.loxya import CONNECTION, set_loxya_connection

# pylint: disable=unused-argument,protected-access


def test_off_by_default(app):
    """Without LOXYA_ENABLED, the API is off even when fully configured.

    This is what keeps the integration out of the way of every other club.
    """
    app.config["LOXYA_ENABLED"] = False
    set_loxya_connection()
    client = loxya.LoxyaApi()

    assert not loxya.feature_enabled()
    assert client.disabled()
    with pytest.raises(loxya.LoxyaError):
        client.get("/api/beneficiaries")


def test_switch_is_not_read_from_the_environment(monkeypatch):
    """LOXYA_ENABLED is set in config.py and instance/config.py only.

    The production runs without environment variables; the team configures it
    through files. An environment variable must not be able to switch the
    integration on.
    """
    import importlib

    import config

    monkeypatch.setenv("LOXYA_ENABLED", "true")
    try:
        assert importlib.reload(config).LOXYA_ENABLED is False
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_connection_settings_are_not_file_settings():
    """The URL and credentials belong to the hot configuration, not config.py.

    Defined in config.py, they would take precedence over what technicians enter.
    """
    import config

    assert not [name for name in CONNECTION if hasattr(config, name)]


def test_connection_settings_come_from_the_database(app):
    """What technicians entered is what the client uses."""
    app.config["LOXYA_ENABLED"] = True
    set_loxya_connection(LOXYA_URL="https://club.loxya.app")

    assert loxya.connection_settings()["LOXYA_URL"] == "https://club.loxya.app"


@pytest.mark.parametrize("missing", sorted(CONNECTION))
def test_enabled_but_incomplete_stays_off(app, missing):
    """Switched on, but a connection setting is still to be entered: no call.

    The integration shows — technicians must see where to enter it — but the API
    stays off.
    """
    app.config["LOXYA_ENABLED"] = True
    set_loxya_connection(**{missing: ""})

    assert loxya.feature_enabled()
    assert loxya.missing_settings() == [missing]
    assert loxya.LoxyaApi().disabled()


def test_enabled_and_configured(app):
    """The switch plus the three connection settings turn the API on."""
    app.config["LOXYA_ENABLED"] = True
    set_loxya_connection()

    assert loxya.configured()
    assert not loxya.LoxyaApi().disabled()


def test_new_token_when_credentials_change(loxya_session):
    """Technicians may change the credentials live: the cached token is dropped."""
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", 200, {"id": 1})

    client.get("/api/beneficiaries/1")
    set_loxya_connection(LOXYA_API_PASSWORD="rotated")
    client.get("/api/beneficiaries/1")

    assert loxya_session.auth_count == 2


def test_token_is_cached(loxya_session):
    """A single authentication serves several calls."""
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", 200, {"id": 1})

    client.get("/api/beneficiaries/1")
    client.get("/api/beneficiaries/1")

    assert loxya_session.auth_count == 1


def test_token_expiry_is_capped(loxya_session):
    """Token reuse never exceeds TOKEN_MAX_LIFETIME, whatever the JWT claims."""
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", 200, {"id": 1})

    client.get("/api/beneficiaries/1")

    assert client._token_expiry <= datetime.now() + loxya.TOKEN_MAX_LIFETIME


def test_reauthenticates_once_on_401(loxya_session):
    """An expired token is renewed and the request replayed, not lost."""
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", 200, {"id": 1})
    loxya_session.token_valid = False

    assert client.get("/api/beneficiaries/1") == {"id": 1}
    assert loxya_session.auth_count == 2


def test_raises_on_repeated_401(loxya_session):
    """A second 401 raises rather than looping forever."""
    client = loxya_session.client
    loxya_session.script(
        "GET", "/api/beneficiaries/1", 401, {"error": {"code": 401, "message": "Nope"}}
    )

    with pytest.raises(loxya.LoxyaAuthError):
        client.get("/api/beneficiaries/1")


def test_validation_error_carries_details(loxya_session):
    """A 400 exposes the per-field details, which is what makes it diagnosable."""
    client = loxya_session.client
    loxya_session.script(
        "POST",
        "/api/beneficiaries",
        400,
        {
            "error": {
                "code": 400,
                "message": "Validation failed.",
                "details": {"pseudo": "Ce champ est obligatoire."},
            }
        },
    )

    with pytest.raises(loxya.LoxyaValidationError) as caught:
        client.post("/api/beneficiaries", json={})

    assert "pseudo" in caught.value.details


@pytest.mark.parametrize(
    "status_code,expected",
    [
        (404, loxya.LoxyaNotFoundError),
        (409, loxya.LoxyaConflictError),
        (500, loxya.LoxyaError),
    ],
)
def test_status_codes_map_to_exceptions(loxya_session, status_code, expected):
    """Each meaningful status code raises its own exception type."""
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", status_code, {})

    with pytest.raises(expected):
        client.get("/api/beneficiaries/1")


def test_empty_body_returns_none(loxya_session):
    """A 204, as answered by DELETE, yields None rather than raising."""
    client = loxya_session.client
    loxya_session.script("DELETE", "/api/beneficiaries/1", 204)

    assert client.delete("/api/beneficiaries/1") is None


def test_authorization_header_is_sent(loxya_session):
    """Every authenticated call carries the bearer token."""
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", 200, {"id": 1})

    client.get("/api/beneficiaries/1")

    _, _, kwargs = loxya_session.calls[0]
    assert kwargs["headers"]["Authorization"].startswith("Bearer ")


def test_timeout_is_always_set(loxya_session):
    """No call may hang: an unresponsive Loxya must not freeze a worker."""
    client = loxya_session.client
    loxya_session.script("GET", "/api/beneficiaries/1", 200, {"id": 1})

    client.get("/api/beneficiaries/1")

    _, _, kwargs = loxya_session.calls[0]
    assert kwargs["timeout"] == 5


def test_decode_token_expiry_reads_exp():
    """The JWT expiry is read without verifying the signature."""
    import base64
    import json

    expiry = int((datetime.now() + timedelta(hours=12)).timestamp())
    payload = base64.urlsafe_b64encode(json.dumps({"exp": expiry}).encode())
    token = f"header.{payload.decode().rstrip('=')}.signature"

    decoded = loxya._decode_token_expiry(token)

    assert decoded is not None
    assert int(decoded.timestamp()) == expiry


def test_decode_token_expiry_survives_garbage():
    """An unreadable token is not an error: the caller falls back on a ceiling."""
    assert loxya._decode_token_expiry("not-a-jwt") is None
    assert loxya._decode_token_expiry("a.b.c") is None
