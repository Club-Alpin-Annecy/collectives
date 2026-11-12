"""Non-regression tests for access control on routes and API endpoints.

These tests target routes that were found unprotected (or wrongly protected)
during the September 2026 security audit.
"""

import json
import os
import shutil
from io import BytesIO

import pytest
from PIL import Image

from collectives.models.upload import UploadedFile
from tests import fixtures

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


def test_available_leaders_autocomplete_requires_event_creator(client, user1):
    """Available leaders autocomplete must refuse anonymous and plain users."""
    url = "/api/available_leaders/autocomplete/?q=aa"
    assert client.get(url).status_code in DENIED

    fixtures.client.login(client, user1)
    assert client.get(url).status_code in DENIED


def test_svg_document_upload_is_refused(leader_client, leader_user_with_event, event1):
    """SVG files can embed scripts and are served verbatim: they must be refused."""
    svg = BytesIO(b'<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>')
    response = leader_client.post(
        f"/api/upload/event/{event1.id}",
        data={"image": (svg, "evil.svg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415


def test_uploaded_documents_served_as_attachments(
    leader_client, leader_user_with_event, event1
):
    """Uploaded documents other than images are downloaded, never displayed:
    a GPX file is served as XML and could run scripts in the site's origin."""
    gpx = BytesIO(
        b'<gpx xmlns:h="http://www.w3.org/1999/xhtml"><h:script>1</h:script></gpx>'
    )
    png = BytesIO()
    Image.new("RGB", (1, 1)).save(png, "PNG")
    png.seek(0)

    responses = {}
    for file, name in ((gpx, "trace.gpx"), (png, "photo.png")):
        responses[name] = leader_client.post(
            f"/api/upload/event/{event1.id}",
            data={"image": (file, name)},
            content_type="multipart/form-data",
        )
        assert responses[name].status_code == 200
    uploads = {upload.name: upload for upload in UploadedFile.query.all()}

    try:
        # Link given to users (Flask-Uploads), and the same file as a static file
        gpx_link = json.loads(responses["trace.gpx"].text)["data"]["filePath"]
        gpx_static = f"/static/uploads/documents/{uploads['trace.gpx'].path}"
        for url in (gpx_link, gpx_static):
            with leader_client.get(url) as response:
                assert response.status_code == 200
                assert response.headers["Content-Disposition"] == "attachment"

        png_static = f"/static/uploads/documents/{uploads['photo.png'].path}"
        with leader_client.get(png_static) as response:
            assert response.status_code == 200
            assert response.headers["Content-Disposition"].startswith("inline")
    finally:
        for upload in uploads.values():
            os.remove(upload.full_path())


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


def test_security_headers(client):
    """Defensive headers are present on every response."""
    response = client.get("/collectives/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Referrer-Policy" in response.headers
    assert "Strict-Transport-Security" not in response.headers

    response = client.get(
        "/collectives/", environ_overrides={"HTTP_X_FORWARDED_PROTO": "https"}
    )
    assert "Strict-Transport-Security" in response.headers


def test_session_cookie_flags(client, user1):
    """Session cookie is HttpOnly, SameSite and (outside debug) Secure."""
    from tests.fixtures.user import PASSWORD

    response = client.post(
        "/auth/login", data={"login": user1.mail, "password": PASSWORD}
    )
    cookies = [h for h in response.headers.getlist("Set-Cookie") if "session=" in h]
    assert cookies
    for cookie in cookies:
        assert "HttpOnly" in cookie
        assert "SameSite=Lax" in cookie
        assert "Secure" in cookie


def test_private_assets_never_served(app, client, admin_user):
    """Files of the private upload set (e.g. ``SecretFile`` configuration items)
    are only read by the server: nobody may download them, not even an admin."""
    item_folder = os.path.join(app.config["UPLOADED_PRIVATE_DEST"], "TEST_ITEM")
    os.makedirs(os.path.join(item_folder, "v1"), exist_ok=True)
    with open(os.path.join(item_folder, "v1", "secret.png"), "wb") as file:
        file.write(b"secret")
    url = "/_uploads/private/TEST_ITEM/v1/secret.png"

    try:
        with client.get(url) as response:
            assert response.status_code in (302, 404)
            assert b"secret" not in response.data

        fixtures.client.login(client, admin_user, app.config["ADMINPWD"])
        with client.get(url) as response:
            assert response.status_code in (302, 404)
            assert b"secret" not in response.data
    finally:
        shutil.rmtree(item_folder)
