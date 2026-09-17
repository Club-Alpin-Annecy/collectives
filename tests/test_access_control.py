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


def test_svg_document_upload_is_refused(leader_client, leader_user_with_event, event1):
    """SVG files can embed scripts and are served verbatim: they must be refused."""
    from io import BytesIO

    svg = BytesIO(b'<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>')
    response = leader_client.post(
        f"/api/upload/event/{event1.id}",
        data={"image": (svg, "evil.svg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415


@pytest.mark.parametrize(
    "next_url",
    [
        "/\\evil.example",
        "//evil.example",
        "https://evil.example/",
        "javascript:alert(1)",
    ],
)
def test_login_next_open_redirect(client, user1, next_url):
    """The ``next`` parameter of the login page must not redirect off-site."""
    from tests.fixtures.user import PASSWORD

    response = client.post(
        "/auth/login",
        query_string={"next": next_url},
        data={"login": user1.mail, "password": PASSWORD},
    )
    assert response.status_code == 302
    assert "evil.example" not in response.headers["Location"]
    assert "javascript" not in response.headers["Location"]


def test_login_next_local_redirect(client, user1):
    """A local ``next`` parameter is honoured after login."""
    from tests.fixtures.user import PASSWORD

    response = client.post(
        "/auth/login",
        query_string={"next": "/collectives/"},
        data={"login": user1.mail, "password": PASSWORD},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/collectives/")
