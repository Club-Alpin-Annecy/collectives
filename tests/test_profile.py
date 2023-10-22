""" Module to test user profile pages. """

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


def test_show_user_profile_to_leader(leader_client, user1):
    """Test leader access to a user profile."""

    response = leader_client.get(f"profile/user/{user1.id}")
    assert response.status_code == 200
    assert user1.full_name() in response.text
    assert user1.license in response.text
    assert user1.mail in response.text


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
    assert client.login(user1_client, user1) == False
    assert client.login(user1_client, user1, "tEst1234+") == True


def test_change_password_no_modification(user1_client, user1):
    """Test if password do not change if no new password is sent."""
    response = user1_client.get("/profile/user/edit")
    data = utils.load_data_from_form(response.text, "basic_form")

    # No password modification
    response = user1_client.post("/profile/user/edit", data=data)
    assert response.status_code == 302
    assert response.location == "/profile/user/edit"
    assert client.login(user1_client, user1) == True


def test_change_password_wrong_confirm(user1_client, user1):
    """Test if password do not change if confirm password is wrong"""
    response = user1_client.get("/profile/user/edit")
    data = utils.load_data_from_form(response.text, "basic_form")

    # Password modification to tEst1234+ with wrong confirm
    data["password"] = "tEst1234+"
    data["confirm"] = "++++"
    response = user1_client.post("/profile/user/edit", data=data)
    assert response.status_code == 200
    assert client.login(user1_client, user1, "tEst1234+") == False
    assert client.login(user1_client, user1) == True


def test_change_password_unacceptable(user1_client, user1):
    """Test password change using profile update."""
    response = user1_client.get("/profile/user/edit")
    data = utils.load_data_from_form(response.text, "basic_form")

    # Password modification to non acceptable password
    data["password"] = "test123"
    data["confirm"] = "test123"
    response = user1_client.post("/profile/user/edit", data=data)
    assert response.status_code == 200
    assert client.login(user1_client, user1, "test123") == False
    assert client.login(user1_client, user1) == True
