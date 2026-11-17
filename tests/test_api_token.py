"""Tests of the authentication by API token and of the event descriptions."""

from datetime import timedelta

from flask import g

from collectives.models import ApiToken, RoleIds, db
from collectives.utils.time import current_time
from tests.fixtures.client import login, logout

# pylint: disable=unused-argument

EVENTS_URL = "/api/events/?page=1&size=25&description=1"


def create_token(user) -> str:
    """Create an API token for a user.

    :param user: The owner of the token
    :return: The clear token
    """
    api_token, clear_token = ApiToken.create(user, "Test")
    db.session.add(api_token)
    db.session.commit()
    return clear_token


def request(client, url: str, token: str = None, method: str = "GET"):
    """Send a request, optionally authenticated by an API token.

    Tests share one application context, in which Flask-Login caches the user
    of the previous request: forget it, as a real request would start without.

    :param client: The test client
    :param url: The URL to request
    :param token: The clear API token to send, if any
    :param method: The HTTP method
    :return: The response
    """
    g.pop("_login_user", None)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.open(url, method=method, headers=headers)


def test_description_hidden_from_anonymous(client, event1):
    """The description is not part of the public event list."""
    response = request(client, EVENTS_URL)
    assert response.status_code == 200
    assert len(response.json["data"]) == 1
    assert "description" not in response.json["data"][0]


def test_description_for_logged_user(user1_client, event1):
    """A logged user gets the description, but only on request."""
    response = user1_client.get(EVENTS_URL)
    assert response.json["data"][0]["description"] == event1.description

    response = user1_client.get("/api/events/?page=1&size=25")
    assert "description" not in response.json["data"][0]


def test_token_authenticates_leader(client, leader_user, event1, draft_event):
    """A token gives its owner's view of the events, with descriptions."""
    token = create_token(leader_user)

    response = request(client, EVENTS_URL, token)
    assert response.status_code == 200
    data = response.json["data"]
    # The leader sees its own draft event, unlike anonymous visitors
    assert {event["id"] for event in data} == {event1.id, draft_event.id}
    assert data[0]["description"] == event1.description

    # No session is opened by the token
    assert "Set-Cookie" not in response.headers
    assert len(request(client, EVENTS_URL).json["data"]) == 1


def test_token_is_stored_hashed(leader_user):
    """Only the digest of the token is kept in database."""
    token = create_token(leader_user)
    api_token = leader_user.api_tokens[0]
    assert api_token.token_hash != token
    assert api_token.token_hash == ApiToken.hash_token(token)
    assert api_token.expiry_date - api_token.creation_date == timedelta(days=90)


def test_refused_tokens(client, leader_user, event1):
    """Unknown and expired tokens are answered 401, not the public list."""
    assert request(client, EVENTS_URL, "unknown").status_code == 401

    token = create_token(leader_user)
    leader_user.api_tokens[0].expiry_date = current_time() - timedelta(days=1)
    db.session.commit()
    assert request(client, EVENTS_URL, token).status_code == 401


def test_token_is_read_only(client, leader_user, event1):
    """A token is refused outside of the event list and for writes."""
    token = create_token(leader_user)

    assert request(client, "/api/users/", token).status_code == 401
    url = f"/api/upload/event/{event1.id}"
    assert request(client, url, token, method="POST").status_code == 401
    # Outside of the API, the token is ignored
    assert request(client, "/profile/api_tokens", token).status_code == 302


def test_token_follows_owner_rights(client, leader_user, event1):
    """A token stops working when its owner is no longer a leader or active."""
    token = create_token(leader_user)
    assert request(client, EVENTS_URL, token).status_code == 200

    leader_user.enabled = False
    db.session.commit()
    assert request(client, EVENTS_URL, token).status_code == 401

    leader_user.enabled = True
    for role in list(leader_user.roles):
        if role.role_id == RoleIds.EventLeader:
            db.session.delete(role)
    db.session.commit()
    assert not leader_user.can_use_api_tokens()
    assert request(client, EVENTS_URL, token).status_code == 401


def test_token_management(client, leader_user, leader2_user, event1):
    """A leader creates a token from its profile, uses it and deletes it."""
    login(client, leader_user)
    response = client.get("/profile/api_tokens")
    assert response.status_code == 200
    assert "Vous n'avez aucun jeton" in response.text

    response = client.post("/profile/api_tokens", data={"name": "Mon script"})
    assert response.status_code == 200
    assert "Mon script" in response.text
    api_token = leader_user.api_tokens[0]
    token = response.text.split('id="new-api-token">')[1].split("<")[0]
    assert ApiToken.find_valid(token) == api_token

    # The clear token is not shown again
    assert token not in client.get("/profile/api_tokens").text

    # Another leader cannot delete it
    login(client, leader2_user)
    url = f"/profile/api_tokens/{api_token.id}/delete"
    client.post(url)
    assert ApiToken.query.count() == 1

    login(client, leader_user)
    assert client.post(url).status_code == 302
    assert ApiToken.query.count() == 0
    logout(client)
    assert request(client, EVENTS_URL, token).status_code == 401


def test_token_reserved_to_leaders(user1_client):
    """A user without a leader role cannot create a token."""
    assert user1_client.get("/profile/api_tokens").status_code == 302
    response = user1_client.post("/profile/api_tokens", data={"name": "Mon script"})
    assert response.status_code == 302
    assert ApiToken.query.count() == 0


def test_account_deletion_removes_tokens(client, leader_user, event1):
    """Deleting an account deletes its tokens."""
    token = create_token(leader_user)
    leader_user.anonymize()
    db.session.commit()
    assert ApiToken.query.count() == 0
    assert request(client, EVENTS_URL, token).status_code == 401
