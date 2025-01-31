"""Leader autocomplete tests."""

from collectives import models

# pylint: disable=unused-argument


def get_url(query, target="leaders", max_returns=8):
    """Creates the url to search for the query

    :param string query: the name part to find
    :param int max: the maximum number of returned users.
    :returns: the url to the autocomplete api"""
    return f"/api/{target}/autocomplete/?q={query}&l={max_returns}"


def test_search_leaders(
    user1_client, user2, leader_user_with_event, leader2_user_with_event
):
    """Test to find Paterson users with autocomplete"""
    response = user1_client.get(get_url("Eva"))
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["full_name"] == "Evan PRZEWODNIK"


def test_search_no_found(
    user1_client, user2, leader_user_with_event, leader2_user_with_event
):
    """Test to check the response if nothing is found"""
    response = user1_client.get(get_url("xxx"))
    assert response.status_code == 200
    assert len(response.json) == 0


def test_search_available_leaders(leader_client, user2, leader_user, leader2_user):
    """Test to find available leader with autocomplete for leader affectation."""
    aid = models.ActivityType.query.filter_by(name="Alpinisme").first().id
    response = leader_client.get(get_url("Eva", "available_leaders") + f"&aid={aid}")
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["full_name"] == "Evan PRZEWODNIK"
