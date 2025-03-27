"""Test account creation of local user (ie not attached to
FFCAM extranet)"""

# pylint: disable=redefined-outer-name, unused-argument, unused-import


import pytest

from tests import utils
from tests.mock.mail import mail_success_monkeypatch
from tests.mock.extranet import extranet_monkeypatch, local_accounts, VALID_LICENSE, EXPIRED_LICENSE
from collectives.models import db, ConfirmationToken, User, UserType
from collectives.models import ConfirmationTokenType, Configuration


@pytest.fixture
def example_data():
    """Random data to create a local account"""
    return {
        "mail": "test@example.org",
        "first_name": "Jane",
        "last_name": "Doe",
        "phone": "06 32 32 32 32",
        "emergency_contact_name": "Mark Doe",
        "emergency_contact_phone": "01 25 25 25 25",
        "license": "740000000000",
        "date_of_birth": "1950-12-12",
        "password": "Test1234!",
        "confirm": "Test1234!",
        "submit": "Créer le compte",
        "gender": "1",
        "legal_accepted": "y",
    }


def test_local_valid_signup(client, example_data, mail_success_monkeypatch, local_accounts):
    """Valid signup of a user"""


    response = client.get("/auth/signup")
    assert response.status_code == 200

    assert isinstance(utils.load_data_from_form(response.text, "basic_form"), dict)

    response = client.post("/auth/signup", data=example_data)
    assert utils.get_form_errors(response.text) == []
    assert response.status_code == 302

    user = db.session.query(User).filter(User.mail == example_data["mail"]).first()
    assert user is not None
    assert user.type == UserType.UnverifiedLocal

    token = (
        db.session.query(ConfirmationToken)
        .filter(ConfirmationToken.existing_user_id == user.id)
        .first()
    )
    assert token is not None
    assert token.token_type == ConfirmationTokenType.ActivateAccount

    assert mail_success_monkeypatch.sent_mail_count() == 1

    response = client.post(
        "/auth/login",
        data={"mail": example_data["mail"], "password": example_data["password"]},
    )
    assert response.headers["Location"] in [
        "http://localhost/auth/login",
        "/auth/login",
    ]

    response = client.get("auth/process_confirmation/" + token.uuid)
    assert response.status_code == 302

    response = client.post(
        "/auth/login",
        data={"mail": example_data["mail"], "password": example_data["password"]},
    )
    assert response.headers["Location"] in ["http://localhost/", "/"]


def test_local_signup_no_phone(client, example_data, mail_success_monkeypatch, local_accounts):
    """Invalid signup of a user"""

    response = client.get("/auth/signup")
    assert response.status_code == 200

    example_data["phone"] = ""

    response = client.post("/auth/signup", data=example_data)

    assert len(utils.get_form_errors(response.text)) >= 1

    user = db.session.query(User).filter(User.mail == example_data["mail"]).first()
    assert user is None

    token = (
        db.session.query(ConfirmationToken)
        .filter(ConfirmationToken.user_license == example_data["license"])
        .first()
    )
    assert token is None

    assert mail_success_monkeypatch.sent_mail_count() == 0


def test_local_password_rescue(user1, client, mail_success_monkeypatch, local_accounts):
    """Test to get a new password"""

    user1.type = UserType.Local
    db.session.add(user1)
    db.session.commit()

    response = client.get("/auth/recover")
    assert response.status_code == 200

    data = {
        "mail": user1.mail,
        "license": user1.license,
        "date_of_birth": user1.date_of_birth,
    }

    response = client.post("/auth/recover", data=data)
    assert response.status_code == 302

    assert mail_success_monkeypatch.sent_mail_count() == 1

    token = (
        db.session.query(ConfirmationToken)
        .filter(ConfirmationToken.existing_user_id == user1.id)
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
        "/auth/login", data={"mail": user1.mail, "password": "TTaa123++"}
    )
    assert response.headers["Location"] in ["http://localhost/", "/"]


def test_extranet_password_rescue(
    extranet_user, client, mail_success_monkeypatch, extranet_monkeypatch
):
    """Test to get a new password and new license"""
    
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
        "/auth/login", data={"mail": extranet_user.mail, "password": "TTaa123++"}
    )
    assert response.headers["Location"] in ["http://localhost/", "/"]

    assert extranet_user.license == VALID_LICENSE
