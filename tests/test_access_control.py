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
