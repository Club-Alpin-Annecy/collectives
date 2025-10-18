"""Module to test extranet calls"""

# pylint: disable=unused-argument

from collectives.models import (
    ConfirmationToken,
    ConfirmationTokenType,
    User,
    UserType,
    db,
)
from tests import fixtures, mock, utils
from tests.mock.extranet import (
    EXPIRED_LICENSE,
    VALID_LICENSE,
    VALID_LICENSE_WITH_NO_EMAIL,
    VALID_LICENSES,
    VALID_USER_EMAIL,
    VALID_USER_EMERGENCY,
)
from tests.mock.mail import mail_success_monkeypatch


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
            data = {"login": user.mail, "password": fixtures.user.PASSWORD}
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


def test_extranet_password_rescue(
    extranet_user, client, extranet_monkeypatch, mail_success_monkeypatch
):
    """Test to get a new password and new license."""

    extranet_user.type = UserType.Extranet
    extranet_user.license = EXPIRED_LICENSE
    db.session.add(extranet_user)
    db.session.commit()

    response = client.get("/auth/recover")
    assert response.status_code == 200

    data = {
        "mail": extranet_user.mail,
        "license": VALID_LICENSE,
        "date_of_birth": extranet_user.date_of_birth,
    }

    response = client.post("/auth/recover", data=data)

    assert mail_success_monkeypatch.sent_mail_count() == 1

    assert response.status_code == 302

    token = (
        db.session.query(ConfirmationToken)
        .filter(ConfirmationToken.existing_user_id == extranet_user.id)
        .first()
    )
    assert token is not None
    assert token.token_type == ConfirmationTokenType.RecoverAccount

    response = client.get("auth/process_confirmation/" + token.uuid)
    assert response.status_code == 200

    data = {"password": "TTaa123++", "confirm": "TTaa123++"}
    response = client.post("auth/process_confirmation/" + token.uuid, data=data)
    assert response.status_code == 302

    response = client.post(
        "/auth/login", data={"login": extranet_user.mail, "password": "TTaa123++"}
    )
    assert response.headers["Location"] in ["http://localhost/", "/"]

    assert extranet_user.license == VALID_LICENSE


def test_extranet_password_rescue_duplicate_mail(
    extranet_user, user1, client, extranet_monkeypatch, mail_success_monkeypatch
):
    """Test to get a new password in case of double email.

    user1 is an user to check what happens in case of double email"""

    user1.mail = extranet_user.mail
    db.session.add(user1)
    db.session.commit()

    response = client.get("/auth/recover")
    assert response.status_code == 200

    data = {
        "mail": extranet_user.mail,
        "license": VALID_LICENSE,
        "date_of_birth": extranet_user.date_of_birth,
    }

    response = client.post("/auth/recover", data=data)

    assert mail_success_monkeypatch.sent_mail_count() == 1

    assert response.status_code == 302


def test_extranet_password_rescue_expiration_duplicate_mail(
    extranet_user, user1, client, extranet_monkeypatch, mail_success_monkeypatch
):
    """Test to get a new password and new license.

    user1 is an user to check what happens in case of double email"""

    extranet_user.type = UserType.Extranet
    extranet_user.license = EXPIRED_LICENSE
    db.session.add(extranet_user)
    user1.mail = extranet_user.mail
    db.session.add(user1)
    db.session.commit()

    response = client.get("/auth/recover")
    assert response.status_code == 200

    data = {
        "mail": extranet_user.mail,
        "license": VALID_LICENSE,
        "date_of_birth": extranet_user.date_of_birth,
    }

    response = client.post("/auth/recover", data=data)

    assert mail_success_monkeypatch.sent_mail_count() == 1

    assert response.status_code == 302


def test_extranet_duplicate_signup(
    extranet_user, client, mail_success_monkeypatch, extranet_monkeypatch
):
    """Invalid signup of a user with an existing account"""

    # Same license
    data = {
        "mail": extranet_user.mail,
        "license": extranet_user.license,
        "date_of_birth": extranet_user.date_of_birth,
    }
    response = client.post("/auth/signup", data=data)
    assert len(utils.get_form_errors(response.text)) >= 1


def test_extranet_same_email_signup(
    extranet_user, client, mail_success_monkeypatch, extranet_monkeypatch
):
    """Signup of a user with a mail already used by an account"""

    data = {
        "mail": extranet_user.mail,
        "license": VALID_LICENSES[1],
        "date_of_birth": extranet_user.date_of_birth,
    }
    response = client.post("/auth/signup", data=data)
    assert len(utils.get_form_errors(response.text)) == 0
