"""Module to test api"""

import pytest


@pytest.mark.parametrize("path", ("/api/users/",))
def test_login_required(client, path):
    """Test if unauthenticated acces is rejected."""
    assert client.get(path).status_code == 302


def test_models_js_cache(client):
    """Test that browsers may reuse models.js between pages."""
    response = client.get("/api/models.js")
    assert response.status_code == 200
    assert response.cache_control.public
    assert response.cache_control.max_age > 0
    assert "const EnumEventStatus=" in response.text
