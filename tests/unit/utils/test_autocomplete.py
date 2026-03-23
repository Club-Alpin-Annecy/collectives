"""Unit tests for user name auto-completion"""

import pytest

from collectives.api.autocomplete_user import _make_autocomplete_query
from collectives.api.event import _normalize_search_term
from collectives.models import db


def test_autocomplete(user1, user2):
    """Test fuzzy user name matching"""
    user1.first_name = "First"
    user1.last_name = "User"

    user2.first_name = "Second"
    user2.last_name = "User"

    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()

    users = list(_make_autocomplete_query("user").all())
    assert len(users) == 2
    assert users[0] == user1
    users = list(_make_autocomplete_query("rst u").all())
    assert len(users) == 1
    assert users[0].mail == "user1@example.org"
    users = list(_make_autocomplete_query("sec").all())
    assert len(users) == 1
    assert users[0].mail == "user2@example.org"
    users = list(_make_autocomplete_query("z").all())
    assert len(users) == 0

    user1.enabled = False
    users = list(_make_autocomplete_query("user").all())
    assert len(users) == 2
    assert users[0] == user2


# ---------------------------------------------------------------------------
# _normalize_search_term
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Accents are stripped
        ("éléphant", "elephant"),
        ("Réunion", "Reunion"),
        # Apostrophes become spaces
        ("l'ascension", "l ascension"),
        ("aujourd'hui", "aujourd hui"),
        # Hyphens become spaces
        ("Mont-Blanc", "Mont Blanc"),
        # Mixed: accent + apostrophe
        ("L'Île-de-France", "L Ile de France"),
        # Already clean string is unchanged
        ("alpinisme", "alpinisme"),
        # Leading/trailing whitespace is stripped
        ("  test  ", "test"),
    ],
)
def test_normalize_search_term(raw, expected):
    """_normalize_search_term strips accents, apostrophes and punctuation."""
    assert _normalize_search_term(raw) == expected


# ---------------------------------------------------------------------------
# Python ↔ SQL normalisation consistency
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title",
    [
        "École d'aventure au Mont-Blanc",
        "Ski/raquettes (débutants)",
        "Atelier : cartographie",
        "Réunion!",
        "Château de Grächèn",
        "Königssee, très beau",
        "Señor López",
    ],
)
def test_python_and_sql_normalize_match(app, title):
    """The SQL-side normalisation must produce the same result as the Python side.

    This catches any character that _normalize_search_term handles but
    _SQL_NORMALIZE_MAP does not (or vice-versa).
    """
    from datetime import date, timedelta

    from collectives.api.event import _sql_normalized_title

    # Create a temporary event with the given title
    from collectives.models import ActivityType, Event, EventType, db

    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    event_type = EventType.query.filter_by(name="Collective").first()
    now = date.today()

    event = Event()
    event.title = title
    event.start = now + timedelta(days=1)
    event.end = now + timedelta(days=1)
    event.registration_open_time = now
    event.registration_close_time = now + timedelta(days=1)
    event.num_online_slots = 0
    event.activity_types.append(alpinisme)
    event.event_type = event_type
    event.set_rendered_description("x")
    db.session.add(event)
    db.session.flush()

    # Query the SQL-side normalised value
    sql_result = (
        db.session.query(_sql_normalized_title())
        .filter(Event.id == event.id)
        .scalar()
    )

    python_result = _normalize_search_term(title)

    # ilike is case-insensitive, so compare lowercased
    assert sql_result.lower().strip() == python_result.lower()

    db.session.rollback()
