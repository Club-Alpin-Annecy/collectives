""" " Testing authentication"""

from datetime import datetime

from tests.fixtures import user


def test_wrong_login(client, app):
    """ "Invalide login redirected to login page"""
    response = client.post(
        "/auth/login", data={"login": "unknown", "password": app.config["ADMINPWD"]}
    )
    assert response.headers["Location"] in [
        "http://localhost/auth/login",
        "/auth/login",
    ]


def test_login(client, app):
    """ "Valid login redirected to home page"""
    response = client.post(
        "/auth/login", data={"login": "admin", "password": app.config["ADMINPWD"]}
    )
    assert response.headers["Location"] in ["http://localhost/", "/"]


def test_spam_protection(client, user1):
    """ "Invalide login redirected to login page"""
    response = client.post(
        "/auth/login", data={"login": user1.mail, "password": "wRONG"}
    )
    assert response.location in [
        "http://localhost/auth/login",
        "/auth/login",
    ]

    response = client.post(
        "/auth/login", data={"login": user1.mail, "password": user.PASSWORD}
    )
    assert response.location == "/auth/login"

    user1.last_failed_login = datetime(2000, 1, 1)
    response = client.post(
        "/auth/login", data={"login": user1.mail, "password": user.PASSWORD}
    )
    assert response.location == "/"


def test_login_same_email(client, app, user1, user101_same_email):
    """Tests login with non-unique email addresses"""
    # Connection with user1
    response = client.post(
        "/auth/login",
        data={"login": user1.mail, "password": user.PASSWORD},
        follow_redirects=True,
    )
    assert "Merci de sélectionner votre compte" in response.text

    response = client.post(
        "/auth/login",
        data={"login": user1.mail, "password": user.PASSWORD},
        follow_redirects=True,
    )
    assert user1.full_name() in response.text

    response = client.post("/auth/logout")

    # Connection with user101
    response = client.post(
        "/auth/login",
        data={"login": user101_same_email.mail, "password": user.PASSWORD},
        follow_redirects=True,
    )
    assert user101_same_email.full_name() in response.text
