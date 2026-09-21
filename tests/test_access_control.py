"""Non-regression tests for access control on routes and API endpoints.

These tests target routes that were found unprotected (or wrongly protected)
during the September 2026 security audit. See ``doc/SECURITY_AUDIT_2026-09.md``.
"""

import pytest

DENIED = (302, 401, 403)
"""HTTP status codes considered as an access refusal."""


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/upload/event/abc"),
        ("get", "/api/upload/event/abc/list"),
        ("get", "/api/upload/activity_documents/list"),
        ("post", "/api/upload/delete/1"),
    ],
)
def test_upload_api_requires_login(client, method, path):
    """Upload API must refuse anonymous users."""
    response = getattr(client, method)(path)
    assert response.status_code in DENIED


def test_public_leader_autocomplete_hides_license(client, leader_user_with_event):
    """Anonymous leader autocomplete must not expose license numbers."""
    pattern = leader_user_with_event.first_name[:3].lower()
    response = client.get(f"/api/leaders/autocomplete/?q={pattern}")
    assert response.status_code == 200
    results = response.get_json(force=True)
    assert results
    for result in results:
        assert "license" not in result
        assert "mail" not in result


def test_available_leaders_autocomplete_requires_event_creator(client, user1_client):
    """Available leaders autocomplete must refuse anonymous and plain users."""
    assert client.get("/api/available_leaders/autocomplete/?q=aa").status_code in DENIED
    assert (
        user1_client.get("/api/available_leaders/autocomplete/?q=aa").status_code
        in DENIED
    )
