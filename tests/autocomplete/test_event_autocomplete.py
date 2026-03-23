"""Event autocomplete API tests.

Covers: title search, ID lookup (#N), accent- and punctuation-insensitive
search, reverse-date ordering, and result limit.
"""

from datetime import date, timedelta

import pytest

from collectives.models import Event, db

# pylint: disable=unused-argument


def get_url(query, max_returns=12, **kwargs):
    """Build the autocomplete URL.

    :param str query: Search term.
    :param int max_returns: Maximum results to request.
    :returns: URL string.
    """
    url = f"/api/event/autocomplete/?q={query}&l={max_returns}"
    for key, value in kwargs.items():
        url += f"&{key}={value}"
    return url


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def three_events_different_dates(app, leader_user):
    """Three events with different start dates for ordering tests."""
    from collectives.models import ActivityType, EventType

    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    event_type = EventType.query.filter_by(name="Collective").first()
    now = date.today()

    events = []
    for i, delta in enumerate([1, 10, 20]):
        event = Event()
        event.title = f"Sortie commune {i}"
        event.start = now + timedelta(days=delta)
        event.end = now + timedelta(days=delta)
        event.registration_open_time = now - timedelta(days=5)
        event.registration_close_time = now + timedelta(days=5)
        event.num_online_slots = 1
        event.activity_types.append(alpinisme)
        event.event_type = event_type
        event.leaders = [leader_user]
        event.main_leader = leader_user
        event.set_rendered_description("desc")
        db.session.add(event)
        events.append(event)

    db.session.commit()
    return events


# ---------------------------------------------------------------------------
# Basic title search
# ---------------------------------------------------------------------------


def test_search_event_by_title(user1_client, event1):
    """A substring of the title should return the matching event."""
    response = user1_client.get(get_url("New collective"))
    assert response.status_code == 200
    assert any(e["id"] == event1.id for e in response.json)


def test_search_event_no_results(user1_client, event1):
    """An unmatched query should return an empty list."""
    response = user1_client.get(get_url("zzznomatch"))
    assert response.status_code == 200
    assert response.json == []


def test_search_requires_two_chars(user1_client, event1):
    """A single-character query (non-ID) should return no results."""
    response = user1_client.get(get_url("N"))
    assert response.status_code == 200
    assert response.json == []


# ---------------------------------------------------------------------------
# Explicit ID lookup  (#N)
# ---------------------------------------------------------------------------


def test_search_event_by_hash_id(user1_client, event1):
    """#<id> should return exactly the event with that id."""
    # Use %23 so the '#' is sent to the server, not treated as a URL fragment
    response = user1_client.get(get_url(f"%23{event1.id}"))
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["id"] == event1.id


def test_search_event_by_hash_id_no_title_match(user1_client, event1, event2):
    """#<id> must NOT return events whose title contains that number."""
    # Create an event whose title embeds the number; only the exact ID should match
    event2.title = f"Event number {event1.id} in title"
    db.session.commit()

    response = user1_client.get(get_url(f"%23{event1.id}"))
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]["id"] == event1.id


def test_search_event_by_plain_id(user1_client, event1):
    """A plain integer (without #) should also match the event by id."""
    response = user1_client.get(get_url(str(event1.id)))
    assert response.status_code == 200
    assert any(e["id"] == event1.id for e in response.json)


# ---------------------------------------------------------------------------
# Accent- and punctuation-insensitive search
# ---------------------------------------------------------------------------


@pytest.fixture
def event_ecole(app, leader_user):
    """Event with accents, apostrophes and spaces in the title."""
    from collectives.models import ActivityType, EventType

    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    event_type = EventType.query.filter_by(name="Collective").first()
    now = date.today()

    event = Event()
    event.title = "École d'aventure au Mont Blanc"
    event.start = now + timedelta(days=5)
    event.end = now + timedelta(days=5)
    event.registration_open_time = now - timedelta(days=5)
    event.registration_close_time = now + timedelta(days=5)
    event.num_online_slots = 1
    event.activity_types.append(alpinisme)
    event.event_type = event_type
    event.leaders = [leader_user]
    event.main_leader = leader_user
    event.set_rendered_description("desc")
    db.session.add(event)
    db.session.commit()
    return event


@pytest.fixture
def event_ecole_hyphenated(app, leader_user):
    """Event with hyphens, no accents, no apostrophes in the title."""
    from collectives.models import ActivityType, EventType

    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    event_type = EventType.query.filter_by(name="Collective").first()
    now = date.today()

    event = Event()
    event.title = "ecole d aventure au mont-blanc"
    event.start = now + timedelta(days=3)
    event.end = now + timedelta(days=3)
    event.registration_open_time = now - timedelta(days=5)
    event.registration_close_time = now + timedelta(days=5)
    event.num_online_slots = 1
    event.activity_types.append(alpinisme)
    event.event_type = event_type
    event.leaders = [leader_user]
    event.main_leader = leader_user
    event.set_rendered_description("desc")
    db.session.add(event)
    db.session.commit()
    return event


def test_clean_query_matches_accented_punctuated_title(user1_client, event_ecole):
    """'ecole d aventure au mont-blanc' must match 'École d'aventure au Mont Blanc'."""
    response = user1_client.get(get_url("ecole d aventure au mont-blanc"))
    assert response.status_code == 200
    assert any(e["id"] == event_ecole.id for e in response.json)


def test_accented_punctuated_query_matches_clean_title(
    user1_client, event_ecole_hyphenated
):
    """'École d'aventure au Mont Blanc' must match 'ecole d aventure au mont-blanc'."""
    response = user1_client.get(
        get_url("\u00c9cole d%27aventure au Mont Blanc")
    )
    assert response.status_code == 200
    assert any(e["id"] == event_ecole_hyphenated.id for e in response.json)


# ---------------------------------------------------------------------------
# Result ordering
# ---------------------------------------------------------------------------


def test_search_results_sorted_by_reverse_date(
    user1_client, three_events_different_dates
):
    """Results must be sorted by descending start date (most recent first)."""
    response = user1_client.get(get_url("Sortie commune"))
    assert response.status_code == 200
    results = response.json
    assert len(results) == 3

    starts = [r["start"] for r in results]
    assert starts == sorted(starts, reverse=True)


# ---------------------------------------------------------------------------
# Result limit
# ---------------------------------------------------------------------------


def test_search_result_limit(user1_client, app, leader_user):
    """At most l results should be returned."""
    from collectives.models import ActivityType, EventType

    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    event_type = EventType.query.filter_by(name="Collective").first()
    now = date.today()

    for i in range(15):
        e = Event()
        e.title = f"Limitée {i}"
        e.start = now + timedelta(days=i + 1)
        e.end = now + timedelta(days=i + 1)
        e.registration_open_time = now - timedelta(days=5)
        e.registration_close_time = now + timedelta(days=5)
        e.num_online_slots = 1
        e.activity_types.append(alpinisme)
        e.event_type = event_type
        e.leaders = [leader_user]
        e.main_leader = leader_user
        e.set_rendered_description("desc")
        db.session.add(e)
    db.session.commit()

    response = user1_client.get(get_url("Limitée", max_returns=5))
    assert response.status_code == 200
    assert len(response.json) <= 5
