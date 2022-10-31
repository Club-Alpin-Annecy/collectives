""" User autocomplete tests. """

# pylint: disable=unused-argument


def get_url(query, max_returns=8):
    """Creates the url to search for the query

    :param string query: the name part to find
    :param int max: the maximum number of returned users.
    :returns: the url to the autocomplete api"""
    return f"/api/users/autocomplete/?q={query}&l={max_returns}"


def test_search_users(admin_client, user1, user2, user3, user4):
    """Test to find Paterson users with autocomplete"""
    user4.last_name = "Paterson"
    response = admin_client.get(get_url("Pat"))
    assert response.status_code == 200
    assert len(response.json) == 2
    assert response.json[0]["full_name"] == "Kimberly PATERSON"


def test_search_users_full_name(admin_client, user1, user2, user3, user4):
    """Test to find Paterson users using both first and last name"""
    user4.last_name = "Paterson"
    response = admin_client.get(get_url("ly Pat"))
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["full_name"] == "Kimberly PATERSON"


def test_search_no_found(admin_client, user1, user2, user3, user4):
    """Test to check the response if nothing is found"""
    response = admin_client.get(get_url("xxx"))
    assert response.status_code == 200
    assert len(response.json) == 0
