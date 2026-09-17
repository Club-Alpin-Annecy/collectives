"""Tests that administration user filters only accept whitelisted columns (audit M7)."""


def test_user_filter_on_unknown_field_is_ignored(hotline_client):
    """A filter on a non whitelisted attribute (eg password hash) is ignored."""
    base = hotline_client.get("/api/users/?page=1&size=50").get_json()
    filtered = hotline_client.get(
        "/api/users/?page=1&size=50&filters[0][field]=password&filters[0][value]=$"
    ).get_json()
    assert len(filtered["data"]) == len(base["data"])


def test_user_filter_on_known_field(hotline_client, hotline_user):
    """A filter on a whitelisted column still works."""
    response = hotline_client.get(
        "/api/users/?page=1&size=50&filters[0][field]=mail"
        f"&filters[0][value]={hotline_user.mail}"
    )
    data = response.get_json()["data"]
    assert [user["mail"] for user in data] == [hotline_user.mail]


def test_user_sort_on_unknown_field_is_ignored(hotline_client):
    """Sorting on a non column attribute does not crash."""
    response = hotline_client.get(
        "/api/users/?page=1&size=50&sorters[0][field]=avatar_uri&sorters[0][dir]=desc"
    )
    assert response.status_code == 200
    response = hotline_client.get(
        "/api/users/?page=1&size=50&sorters[0][field]=last_name&sorters[0][dir]=desc"
    )
    assert response.status_code == 200
