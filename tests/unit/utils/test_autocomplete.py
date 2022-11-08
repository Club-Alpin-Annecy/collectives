from collectives.api.autocomplete_user import find_users_by_fuzzy_name

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

    users = list(find_users_by_fuzzy_name("user"))
    assert len(users) == 2
    users = list(find_users_by_fuzzy_name("rst u"))
    assert len(users) == 1
    assert users[0].mail == "user1@example.org"
    users = list(find_users_by_fuzzy_name("sec"))
    assert len(users) == 1
    assert users[0].mail == "user2@example.org"
    users = list(find_users_by_fuzzy_name("z"))
    assert len(users) == 0
