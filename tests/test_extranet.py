"""Module to test extranet calls"""

# pylint: disable=unused-argument

from collectives.models import User, db, Configuration
from tests import mock
from tests import fixtures
from tests.mock.extranet import (
    EXPIRED_LICENSE,
    VALID_USER_EMAIL,
    VALID_USER_EMERGENCY,
    VALID_LICENSE_WITH_NO_EMAIL,
)


def test_create_account(client, extranet_monkeypatch):
    """Test valid account creation."""

    # Setup conf as extranet account creation

    # First signup stage
    response = client.get("/auth/signup")
    assert response.status_code == 200
    data = {
        "mail": mock.extranet.VALID_USER_EMAIL,
        "license": mock.extranet.VALID_LICENSE,
        "date_of_birth": mock.extranet.VALID_USER_DOB,
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

    # license from other club
    data = {
        "mail": "test@example.com",
        "license": mock.extranet.OTHER_CLUB_LICENSE,
        "date_of_birth": "2022-10-04",
    }
    response = client.post("/auth/signup", data=data)
    assert response.status_code == 200
    assert "flash-error" in response.text
    assert "licence doit contenir" in response.text


def test_resync_own_account(client, extranet_user, extranet_monkeypatch):
    """Test extranet resync."""

    fixtures.client.login(client, extranet_user)

    response = client.post("/profile/user/force_sync", follow_redirects=True)
    assert response.status_code == 200
    assert "error message" not in response.text

    # sync should have succeeded
    assert extranet_user.emergency_contact_name == "EMERGENCY"

    # test with invalid license -- should redirect to auth page
    extranet_user = client.user
    extranet_user.license = EXPIRED_LICENSE
    db.session.add(extranet_user)
    db.session.commit()
    response = client.post("/profile/user/force_sync", follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/auth/recover"

    fixtures.client.logout(client)


def test_resync_own_account_changed_email(client, extranet_user, extranet_monkeypatch):
    """Test extranet resync with changed email"""
    
    extranet_user.mail = "random@example.org"
    db.session.commit()

    fixtures.client.login(client, extranet_user)

    response = client.post("/profile/user/force_sync", follow_redirects=True)
    assert response.status_code == 200
    assert "error message" in response.text
    assert "adresse email a été modifiée" in response.text
    # sync should have failed
    assert extranet_user.emergency_contact_name != VALID_USER_EMERGENCY

    # test user with no email defined in extranet
    extranet_user = client.user
    extranet_user.license = VALID_LICENSE_WITH_NO_EMAIL
    extranet_user.emergency_contact_name = ""
    db.session.add(extranet_user)
    db.session.commit()
    response = client.post("/profile/user/force_sync", follow_redirects=True)
    assert response.status_code == 200
    assert "error message" in response.text
    assert "pas renseignée " in response.text
    # sync should have failed
    assert extranet_user.emergency_contact_name != VALID_USER_EMERGENCY

    fixtures.client.logout(client)


def test_hotline_resync_account(hotline_client, extranet_user, extranet_monkeypatch):
    """Test extranet resync by hotline user"""

    extranet_user.mail = "random@example.org"
    db.session.commit()
    
    response = hotline_client.post(
        f"/profile/user/{extranet_user.id}/force_sync", follow_redirects=True
    )
    assert response.status_code == 200
    assert "error message" in response.text
    assert "adresse email a été modifiée" in response.text

    extranet_user.mail = VALID_USER_EMAIL
    db.session.commit()

    response = hotline_client.post(
        f"/profile/user/{extranet_user.id}/force_sync", follow_redirects=True
    )
    assert response.status_code == 200
    assert "error message" not in response.text

    response = hotline_client.post(
        "/profile/user/9999999/force_sync", follow_redirects=True
    )
    assert response.status_code == 200
    assert "error message" in response.text

    # Forcing resyng of expired should not redirect
    extranet_user.license = EXPIRED_LICENSE
    db.session.add(extranet_user)
    db.session.commit()

    response = hotline_client.post(
        f"/profile/user/{extranet_user.id}/force_sync", follow_redirects=True
    )
    assert response.status_code == 200
    assert "error message" in response.text
    assert "pas ou plus valide" in response.text

    # Same if license from other club
    extranet_user.license = mock.extranet.OTHER_CLUB_LICENSE
    db.session.add(extranet_user)
    db.session.commit()

    response = hotline_client.post(
        f"/profile/user/{extranet_user.id}/force_sync", follow_redirects=True
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


def test_signup_licence_nocheck(client, extranet_monkeypatch):
    """Test the licence check during signup without club licence check"""

    # First signup stage
    response = client.get("/auth/signup")
    assert response.status_code == 200
    data = {
        "mail": mock.extranet.VALID_USER_EMAIL,
        "license": mock.extranet.VALID_LICENSE,
        "date_of_birth": mock.extranet.VALID_USER_DOB,
    }
    response = client.post("/auth/signup", data=data)
    assert response.status_code == 302
    assert "flash-error" not in response.text
    assert mock.extranet.STORED_TOKEN is not None


def test_signup_licence_check_wrong_club(client, extranet_monkeypatch):
    """Test the not valdi licence during signup with club licence check"""

    # First signup stage
    response = client.get("/auth/signup")
    assert response.status_code == 200
    data = {
        "mail": mock.extranet.VALID_USER_EMAIL,
        "license": mock.extranet.OTHER_CLUB_LICENSE,
        "date_of_birth": mock.extranet.VALID_USER_DOB,
    }
    response = client.post("/auth/signup", data=data)
    assert response.status_code == 200
    assert "flash-error" in response.text
