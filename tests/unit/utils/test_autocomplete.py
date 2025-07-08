"""Unit tests for user name auto-completion"""

from collectives.api.autocomplete_user import _make_autocomplete_query
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
