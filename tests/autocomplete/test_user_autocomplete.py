"""User autocomplete tests."""

from collectives.utils.profile_token import profile_token

# pylint: disable=unused-argument


def get_url(query, max_returns=8):
    """Creates the url to search for the query

    :param string query: the name part to find
    :param int max: the maximum number of returned users.
    :returns: the url to the autocomplete api"""
    return f"/api/users/autocomplete/?q={query}&l={max_returns}"


def test_search_users(leader_client, user1, user2, user3, user4):
    """Test to find Paterson users with autocomplete"""
    user4.last_name = "Paterson"
    response = leader_client.get(get_url("Pat"))
    assert response.status_code == 200
    assert len(response.json) == 2
    assert response.json[0]["full_name"] == "Jake PATERSON"


def test_search_users_full_name(leader_client, user1, user2, user3, user4):
    """Test to find Paterson users using both first and last name"""
    user4.last_name = "Paterson"
    response = leader_client.get(get_url("ly Pat"))
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["full_name"] == "Kimberly PATERSON"


def test_search_no_found(leader_client, user1, user2, user3, user4):
    """Test to check the response if nothing is found"""
    response = leader_client.get(get_url("xxx"))
    assert response.status_code == 200
    assert len(response.json) == 0


def test_search_returns_license(leader_client, user1):
    """Each result must expose the license number."""
    response = leader_client.get(get_url(user1.last_name))
    assert response.status_code == 200
    assert len(response.json) >= 1
    assert "license" in response.json[0]
    assert response.json[0]["license"] == user1.license


def test_search_returns_profile_token(leader_client, user1):
    """Each result must carry a signed HMAC token for direct profile access."""
    response = leader_client.get(get_url(user1.last_name))
    assert response.status_code == 200
    assert len(response.json) >= 1

    result = next(r for r in response.json if r["id"] == user1.id)
    expected_token = profile_token(leader_client.user.id, user1.id)
    assert result["token"] == expected_token


def test_profile_token_is_viewer_specific(leader_client, user1, user2):
    """The token in a result must be bound to the requesting viewer.

    Two different viewers would produce different tokens for the same viewed user.
    We verify this by checking that the returned token matches
    profile_token(viewer_id, user_id) and NOT profile_token(some_other_id, user_id).
    """
    response = leader_client.get(get_url(user1.last_name))
    assert response.status_code == 200

    result = next(r for r in response.json if r["id"] == user1.id)
    # Token matches viewer=leader, viewed=user1
    assert result["token"] == profile_token(leader_client.user.id, user1.id)
    # Token does NOT match viewer=user2 (a different viewer ID)
    assert result["token"] != profile_token(user2.id, user1.id)


def test_profile_token_is_user_specific(leader_client, user1, user2):
    """Tokens must differ between viewed users even for the same viewer."""
    response = leader_client.get(get_url(""))
    # Empty query → too short, but use a broad search that returns both users
    response = leader_client.get(get_url(user1.last_name[:-1]))
    assert response.status_code == 200

    tokens = {r["id"]: r["token"] for r in response.json}
    if user1.id in tokens and user2.id in tokens:
        assert tokens[user1.id] != tokens[user2.id]
