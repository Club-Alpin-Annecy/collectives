"""Module to test user profile pages."""

from flask import url_for

from tests import utils
from tests.fixtures import client

# pylint: disable=unused-argument


def test_show_user_profile(user1_client):
    """Test user access to its profile."""

    user = user1_client.user
    response = user1_client.get(f"profile/user/{user.id}")
    assert response.status_code == 200
    assert user.full_name() in response.text
    assert user.license in response.text
    assert user.mail in response.text


def test_show_user_profile_to_leader_with_event(leader_client, event1_with_reg, user1):
    """Test leader access to a user profile."""

    response = leader_client.get(
        url_for("profile.show_user", user_id=user1.id, event_id=event1_with_reg.id)
    )
    assert response.status_code == 200
    assert user1.full_name() in response.text
    assert user1.license in response.text
    assert user1.mail in response.text


def test_do_not_show_user_profile_to_leader_without_event(leader_client, user2):
    """Test user access to another user profile."""

    response = leader_client.get(f"/profile/user/{user2.id}")
    assert response.status_code == 302


def test_do_not_show_user_profile_to_other(user1_client, user2):
    """Test user access to another user profile."""

    response = user1_client.get(f"/profile/user/{user2.id}")
    assert response.status_code == 302


def test_generate_valid_benevole_cert(client_with_valid_benevole_badge, president_user):
    """Test the volunteer cert generation.

    Does not check the content, just the absence of error."""
    response = client_with_valid_benevole_badge.get("/profile/user/volunteer/cert")
    assert response.status_code == 200
    assert response.content_length > 200000
    assert response.content_type == "application/pdf"


def test_generate_expired_benevole_cert(
    client_with_expired_benevole_badge, president_user
):
    """Test the volunteer cert generation.

    Does not check the content, just the absence of error."""
    response = client_with_expired_benevole_badge.get("/profile/user/volunteer/cert")
    assert response.status_code == 302


def test_change_password(user1_client, user1):
    """Test password change using profile update."""
    response = user1_client.get("/profile/user/edit")
    data = utils.load_data_from_form(response.text, "basic_form")

    # Password modification to tEst1234+
    data["password"] = "tEst1234+"
    data["confirm"] = "tEst1234+"
    response = user1_client.post("/profile/user/edit", data=data)
    assert response.status_code == 302
    assert not client.login(user1_client, user1)
    assert client.login(user1_client, user1, "tEst1234+")


def test_change_password_no_modification(user1_client, user1):
    """Test if password do not change if no new password is sent."""
    response = user1_client.get("/profile/user/edit")
    data = utils.load_data_from_form(response.text, "basic_form")

    # No password modification
    response = user1_client.post("/profile/user/edit", data=data)
    assert response.status_code == 302
    assert response.location == "/profile/user/edit"
    assert client.login(user1_client, user1)


def test_change_password_wrong_confirm(user1_client, user1):
    """Test if password do not change if confirm password is wrong"""
    response = user1_client.get("/profile/user/edit")
    data = utils.load_data_from_form(response.text, "basic_form")

    # Password modification to tEst1234+ with wrong confirm
    data["password"] = "tEst1234+"
    data["confirm"] = "++++"
    response = user1_client.post("/profile/user/edit", data=data)
    assert response.status_code == 200
    assert not client.login(user1_client, user1, "tEst1234+")
    assert client.login(user1_client, user1)


def test_change_password_unacceptable(user1_client, user1):
    """Test password change using profile update."""
    response = user1_client.get("/profile/user/edit")
    data = utils.load_data_from_form(response.text, "basic_form")

    # Password modification to non acceptable password
    data["password"] = "test123"
    data["confirm"] = "test123"
    response = user1_client.post("/profile/user/edit", data=data)
    assert response.status_code == 200
    assert not client.login(user1_client, user1, "test123")
    assert client.login(user1_client, user1)


def test_delete_user(user1_client, user2):
    """Test self-deleting user profile."""

    # Other user, forbidden
    response = user1_client.get(f"/profile/{user2.id}/delete")
    assert response.status_code == 302
    assert response.location == f"/profile/user/{user2.id}"

    # Delete self
    response = user1_client.get("/profile/delete")
    assert response.status_code == 200
    data = utils.load_data_from_form(response.text, "basic_form")

    # Incorrect confirmation
    data["license"] = "incorrect"
    response = user1_client.post("/profile/delete", data=data)
    assert response.status_code == 200

    # Correct confirmation
    data = utils.load_data_from_form(response.text, "basic_form")
    data["license"] = user1_client.user.license

    response = user1_client.post("/profile/delete", data=data)
    assert response.status_code == 302
    assert response.location == "/auth/login"

    # check user has been anonymised
    assert not user1_client.user.enabled
    assert user1_client.user.first_name == "Compte"
    assert user1_client.user.license == str(user1_client.user.id)
    assert "localhost" in user1_client.user.mail
