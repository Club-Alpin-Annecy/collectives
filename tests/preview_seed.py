"""Fills the database of a pull request preview with the test fixtures.

Not part of the test suite: ``deployment/preview/collectives-preview`` runs
``pytest tests/preview_seed.py`` in the preview container, once, against the
database of the instance (``SQLALCHEMY_DATABASE_URI``).
"""

import pytest

import collectives

# pylint: disable=unused-argument, redefined-outer-name
# pylint: disable=too-many-arguments, too-many-positional-arguments


@pytest.fixture
def app():
    """The application on the database of the instance, kept as it is.

    Overrides the test fixture, which recreates the database."""
    preview_app = collectives.create_app()
    with preview_app.app_context():
        yield preview_app


def test_seed(
    admin_user,
    user5,
    user6,
    user7,
    user8,
    user9,
    user10,
    leader_user,
    leader2_user_with_event,
    president_user,
    supervisor_user,
    hotline_user,
    youth_user,
    minor_user,
    user_with_valid_benevole_badge,
    user_with_expired_benevole_badge,
    event1_with_answers,
    event3,
    event4,
    past_event,
    tagged_event,
    cancelled_event,
    draft_event,
    activity_event,
    paying_event,
    free_paying_event,
    youth_event,
    service_event,
):
    """Creates users of each role and events of each kind, with registrations."""
