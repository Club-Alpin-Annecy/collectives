""" Test administration api endpoints. """

import pytest


@pytest.mark.parametrize("path", ("/api/users/", "/api/leaders/"))
def test_login_required(client, path):
    """Test adminstration api rejection of regular users."""
    assert client.get(path).status_code == 302


def test_api_users(admin_client):
    """Test api endpoint to list users."""
    response = admin_client.get("/api/users/?page=1&size=50")
    assert response.status_code == 200


def test_api_leaders(admin_client):
    """Test api endpoint to list leaders."""
    response = admin_client.get("/api/leaders/")
    assert response.status_code == 200
