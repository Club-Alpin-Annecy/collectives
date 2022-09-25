"""" Testing authentication """

from datetime import datetime
from tests.fixtures import user


def test_wrong_login(client):
    """ "Invalide login redirected to login page"""
    response = client.post(
        "/auth/login", data={"mail": "unknown", "password": "foobar2"}
    )
    assert response.headers["Location"] in [
        "http://localhost/auth/login",
        "/auth/login",
    ]


def test_login(client):
    """ "Valid login redirected to home page"""
    response = client.post("/auth/login", data={"mail": "admin", "password": "foobar2"})
    assert response.headers["Location"] in ["http://localhost/", "/"]


def test_spam_protection(client, user1):
    """ "Invalide login redirected to login page"""
    response = client.post(
        "/auth/login", data={"mail": user1.mail, "password": "wRONG"}
    )
    assert response.location in [
        "http://localhost/auth/login",
        "/auth/login",
    ]

    response = client.post(
        "/auth/login", data={"mail": user1.mail, "password": user.PASSWORD}
    )
    assert response.location == "/auth/login"

    user1.last_failed_login = datetime(2000, 1, 1)
    response = client.post(
        "/auth/login", data={"mail": user1.mail, "password": user.PASSWORD}
    )
    assert response.location == "/"
