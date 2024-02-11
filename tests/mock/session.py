""" Mock functions for session. """

import pytest

@pytest.fixture
def session_monkeypatch(monkeypatch):
    """
    Fixture for monkeypatching the session to track calls to add, commit, and rollback.
    """
    # Initialize containers to track calls
    calls = {
        "add": [],
        "commit": 0,
        "rollback": 0,
    }

    # Define mock functions
    def add_mock(instance):
        calls["add"].append(instance)

    def commit_mock():
        calls["commit"] += 1

    def rollback_mock():
        calls["rollback"] += 1

    # Use monkeypatch to replace the session methods with mocks
    monkeypatch.setattr('collectives.models.db.session.add', add_mock)
    monkeypatch.setattr('collectives.models.db.session.commit', commit_mock)
    monkeypatch.setattr('collectives.models.db.session.rollback', rollback_mock)

    return calls
