""" Module to test extranet calls"""
# pylint: disable=unused-argument

from collectives.models import User, db
from tests import mock
from tests import fixtures


def test_create_account(client, extranet_monkeypatch):
    """Test valid account creation."""

    # First signup stage
    response = client.get("/auth/signup")
    assert response.status_code == 200
    data = {
        "mail": "test@example.com",
        "license": mock.extranet.VALID_LICENSE,
        "date_of_birth": "2022-10-04",
    }
    response = client.post("/auth/signup", data=data)
    assert response.status_code == 302
    assert "flash-error" not in response.text
    assert mock.extranet.STORED_TOKEN is not None

    try:
        # Use token to confirm signup
        response = client.get(
            f"/auth/process_confirmation/{mock.extranet.STORED_TOKEN.uuid}"
        )
        assert response.status_code == 200
        data = {
            "password": fixtures.user.PASSWORD,
            "confirm": fixtures.user.PASSWORD,
            "legal_accepted": 1,
        }
        response = client.post(
            f"/auth/process_confirmation/{mock.extranet.STORED_TOKEN.uuid}", data=data
        )
        assert response.status_code == 302
        assert "flash-error" not in response.text
        user = User.query.filter_by(mail="test@example.com").first()
        assert user is not None

        try:
            # test user login capability
            data = {"mail": user.mail, "password": fixtures.user.PASSWORD}
            response = client.post("/auth/login", data=data, follow_redirects=True)
            assert response.status_code == 200

            response = client.get(f"/profile/user/{user.id}")
            assert response.status_code == 200

        # User cleanup
        finally:
            db.session.delete(user)
            db.session.commit()
    # Token cleanup
    finally:
        db.session.delete(mock.extranet.STORED_TOKEN)
        db.session.commit()


def test_wrong_create_account(client, extranet_monkeypatch):
    """Test valid account creation."""
    # wrong date of birth
    data = {
        "mail": "test@example.com",
        "license": mock.extranet.VALID_LICENSE,
        "date_of_birth": "2000-01-01",
    }
    response = client.post("/auth/signup", data=data)
    assert response.status_code == 200
    assert "flash-error" in response.text

    # wrong email
    data = {
        "mail": "wrong@example.com",
        "license": mock.extranet.VALID_LICENSE,
        "date_of_birth": "2022-10-04",
    }
    response = client.post("/auth/signup", data=data)
    assert response.status_code == 200
    assert "flash-error" in response.text


def test_resync_own_account(user1_client, extranet_monkeypatch):
    """Test extranet resync."""

    response = user1_client.post("/profile/user/force_sync", follow_redirects=True)
    assert response.status_code == 200
    assert "error message" not in response.text


def test_hotline_resync_account(hotline_client, user1, extranet_monkeypatch):
    """Test extranet resync by hotline user"""

    response = hotline_client.post(
        f"/profile/user/{user1.id}/force_sync", follow_redirects=True
    )
    assert response.status_code == 200
    assert "error message" not in response.text

    response = hotline_client.post(
        "/profile/user/9999999/force_sync", follow_redirects=True
    )
    assert response.status_code == 200
    assert "error message" in response.text


def test_user_resync_account(user1_client, user2, extranet_monkeypatch):
    """Test extranet resync by invalid user"""

    response = user1_client.post(
        f"/profile/user/{user2.id}/force_sync", follow_redirects=True
    )
    assert response.status_code == 200
    assert "error message" in response.text
