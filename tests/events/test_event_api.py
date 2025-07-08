"""Test API related to event"""

from datetime import date

from collectives.models import ActivityType, EventTag, db

# pylint: disable=unused-argument,too-many-arguments
# pylint: disable=too-many-positional-arguments


def today():
    """Returns today's date as string"""
    return date.today().strftime("%Y-%m-%d")


def test_event_access(
    user1_client,
    event1,
    event2,
    past_event,
    draft_event,
    cancelled_event,
    activity_event,
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
    assert data[0]["leaders"][0]["full_name"] == "Romeo CAPO"
    assert data[0]["title"] == past_event.title
    assert data[0]["activity_types"][0]["name"] == "Alpinisme"
    assert data[0]["event_type"]["name"] == "Collective"

    # Remove activity_event activity_type -- should still not have access
    activity_event.activity_types.clear()
    db.session.commit()

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start&sorters[0][dir]=asc"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 4


def test_event_access_leader(
    leader_client,
    event1,
    event2,
    past_event,
    draft_event,
    cancelled_event,
    activity_event,
):
    """Test list of event for a leader"""

    response = leader_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start&sorters[0][dir]=asc"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 6
    assert f"/collectives/{past_event.id}" in data[0]["view_uri"]
    assert data[0]["num_online_slots"] == 1
    assert data[0]["leaders"][0]["full_name"] == "Romeo CAPO"
    assert data[0]["title"] == past_event.title
    assert data[0]["activity_types"][0]["name"] == "Alpinisme"
    assert data[0]["event_type"]["name"] == "Collective"

    # Remove activity_event activity_type -- should keep access
    activity_event.activity_types.clear()
    db.session.commit()

    response = leader_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start&sorters[0][dir]=asc"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 6

    # Set activity_type to another activity -- should keep access because leading it
    not_alpinisme = ActivityType.query.filter(ActivityType.name != "Alpinisme").first()
    activity_event.activity_types.append(not_alpinisme)
    db.session.commit()

    response = leader_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start&sorters[0][dir]=asc"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 6

    # Remove from leaders -- should lose access
    activity_event.leaders.clear()
    db.session.commit()

    response = leader_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start&sorters[0][dir]=asc"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 5


def test_event_access_not_passed(
    user1_client, event1, event2, past_event, draft_event, cancelled_event
):
    """Test list of event without past events"""

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=title"
        "&sorters[0][dir]=asc&filters[0][field]=end&filters[0][type]=>%3D"
        f"&filters[0][value]={today()}"
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
    assert data[0]["leaders"][0]["full_name"] == "Romeo CAPO"
    assert data[0]["title"] == "New collective 2"
    assert data[0]["activity_types"][0]["name"] == "Canyon"
    assert data[0]["event_type"]["name"] == "Collective"


def test_event_filter_activity_with_several_types(user1_client, event1, event2, event3):
    """Test list of event with activity filter"""
    event2.activity_types = [ActivityType.query.filter_by(name="Canyon").first()]
    event1.activity_types = [ActivityType.query.filter_by(name="Alpinisme").first()]
    event3.activity_types = [ActivityType.query.filter_by(name="Parapente").first()]

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=title"
        "&sorters[0][dir]=asc&filters[0][field]=activity_type&filters[0][type]=="
        "&filters[0][value]=canyon&filters[1][field]=activity_type&filters[1][type]=="
        "&filters[1][value]=alpinisme"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 2
    assert data[1]["view_uri"] == "/collectives/2-new-collective-2"
    assert data[1]["num_online_slots"] == 1
    assert data[1]["leaders"][0]["full_name"] == "Romeo CAPO"
    assert data[1]["title"] == "New collective 2"
    assert data[1]["activity_types"][0]["name"] == "Canyon"
    assert data[1]["event_type"]["name"] == "Collective"
    assert data[0]["view_uri"] == "/collectives/1-new-collective-1"
    assert data[0]["num_online_slots"] == 1
    assert data[0]["leaders"][0]["full_name"] == "Romeo CAPO"
    assert data[0]["title"] == "New collective 1"
    assert data[0]["activity_types"][0]["name"] == "Alpinisme"
    assert data[0]["event_type"]["name"] == "Collective"


def test_event_filter_service(user1_client, event1, service_event):
    """Test list of event with activity filter"""

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=title"
        "&sorters[0][dir]=asc&filters[0][field]=activity_type&filters[0][type]=="
        "&filters[0][value]=__services"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    assert data[0]["activity_types"][0]["name"] == "Service"


def test_event_filter_tags(user1_client, event1, event2, event3):
    """Test list of event with tag filters"""
    event1.tag_refs.append(EventTag(6))
    event2.tag_refs.append(EventTag(2))

    response = user1_client.get(
        "/api/events/?page=1&size=25&sorters[0][field]=start&sorters[0][dir]=asc"
        f"&filters[0][field]=end&filters[0][type]=>%3D&filters[0][value]={today()}"
        "&filters[1][field]=tags&filters[1][type]=%3D&filters[1][value]=tag_handicaf"
        "&filters[2][field]=tags&filters[2][type]=%3D&filters[2][value]=tag_mountain_protection"
    )
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 2
    assert data[0]["title"] == event1.title
    assert data[0]["tags"][0]["name"] == "Handicaf"
    assert data[1]["title"] == event2.title
    assert data[1]["tags"][0]["name"] == "CPM"


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
