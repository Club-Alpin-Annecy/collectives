"""Module to test extranet calls"""

# pylint: disable=unused-argument

from collectives.models import User, db
from tests import fixtures, mock
from tests.mock.extranet import (
    EXPIRED_LICENSE,
    VALID_LICENSE_WITH_NO_EMAIL,
    VALID_USER_EMAIL,
    VALID_USER_EMERGENCY,
)


def test_resync_own_account(client, extranet_user, extranet_monkeypatch):
    """Test extranet resync."""

    fixtures.client.login(client, extranet_user)

    response = client.post("/profile/user/force_sync", follow_redirects=True)
    assert response.status_code == 200
    assert "error message" not in response.text

    # sync should have succeeded
    assert extranet_user.emergency_contact_name == "EMERGENCY"


def test_resync_own_expired_account(client, extranet_user, extranet_monkeypatch):
    """Test extranet resync with an expired license."""
    # test with invalid license -- should redirect to auth page
    fixtures.client.login(client, extranet_user)
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
