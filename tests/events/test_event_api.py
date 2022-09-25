""" Test API related to event """
from collectives.models import ActivityType

# pylint: disable=unused-argument,too-many-arguments


def test_event_access(
    user1_client, event1, event2, past_event, draft_event, cancelled_event
):
    """Test list of event"""

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start&sorters[0][dir]=asc"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 4
    assert f"/collectives/{past_event.id}" in data[0]["view_uri"]
    assert data[0]["num_online_slots"] == 1
    assert data[0]["leaders"][0]["name"] == "Compte ADMINISTRATEUR"
    assert data[0]["title"] == past_event.title
    assert data[0]["activity_types"][0]["name"] == "Alpinisme"
    assert data[0]["event_types"][0]["name"] == "Collective"


def test_event_access_not_passed(
    user1_client, event1, event2, past_event, draft_event, cancelled_event
):
    """Test list of event without past events"""

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=title"
        "&sorters[0][dir]=asc&filters[0][field]=end&filters[0][type]=>%3D"
        "&filters[0][value]=now"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 3


def test_event_access_not_cancelled(
    user1_client, event1, event2, past_event, draft_event, cancelled_event
):
    """Test list of event without past events"""

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start"
        "&sorters[0][dir]=asc&filters[0][field]=status&filters[0][type]=!%3D"
        "&filters[0][value]=Cancelled"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 3


def test_event_filter_activity(user1_client, event1, event2, event3):
    """Test list of event with activity filter"""
    event2.activity_types = [ActivityType.query.filter_by(name="Canyon").first()]

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=title"
        "&sorters[0][dir]=asc&filters[0][field]=activity_type&filters[0][type]=="
        "&filters[0][value]=canyon"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["view_uri"] == "/collectives/2-new-collective-2"
    assert data[0]["num_online_slots"] == 1
    assert data[0]["leaders"][0]["name"] == "Compte ADMINISTRATEUR"
    assert data[0]["title"] == "New collective 2"
    assert data[0]["activity_types"][0]["name"] == "Canyon"
    assert data[0]["event_types"][0]["name"] == "Collective"


def test_event_filter_tag(user1_client, event1, event2, tagged_event):
    """Test list of event with tag filter"""

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start"
        "&sorters[0][dir]=asc&filters[0][field]=end&filters[0][type]=>%3D&filters[0][value]=now"
        "&filters[1][field]=tags&filters[1][type]=%3D&filters[1][value]=tag_handicaf"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == tagged_event.title
    assert data[0]["tags"][0]["name"] == "Handicaf"


def test_event_title_search(user1_client, event1, event2):
    """Test title search"""

    event2.title = "This is a title"

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start"
        "&sorters[0][dir]=asc&filters[0][field]=title&filters[0][type]=like"
        f"&filters[0][value]={event2.title}"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["title"] == event2.title
