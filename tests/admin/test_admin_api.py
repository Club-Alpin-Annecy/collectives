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


def test_api_users_with_filters(admin_client):
    """Test api endpoint to list users with filters."""
    response = admin_client.get(
        # pylint: disable=line-too-long
        "/api/users/?page=1&size=50&filters[0][field]=roles&filters[0][type]=like&filters[0][value]=r2"
    )
    assert response.status_code == 200


def test_api_users_with_filters_on_badges(admin_client):
    """Test api endpoint to list users with filters."""
    response = admin_client.get(
        # pylint: disable=line-too-long
        "/api/users/?page=1&size=50&filters[0][field]=badges&filters[0][type]=like&filters[0][value]=t1-b1"
    )
    assert response.status_code == 200


def test_api_leaders(admin_client):
    """Test api endpoint to list leaders."""
    response = admin_client.get("/api/leaders/")
    assert response.status_code == 200
