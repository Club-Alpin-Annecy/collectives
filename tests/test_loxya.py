"""Module to test the Loxya API client."""

from datetime import datetime, timedelta

import pytest

from collectives.utils import loxya

# pylint: disable=unused-argument,protected-access


def test_disabled_without_url(app):
    """An empty LOXYA_URL disables the API, so CI never reaches the network."""
    app.config["LOXYA_URL"] = ""
    client = loxya.LoxyaApi()

    assert client.disabled()
    with pytest.raises(loxya.LoxyaError):
        client.get("/api/beneficiaries")


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
