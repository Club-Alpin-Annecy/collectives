"""Fills the database of a pull request preview with the test fixtures.

Not part of the test suite: ``deployment/preview/collectives-preview`` runs
``pytest tests/preview_seed.py`` in the preview container, once, against the
database of the instance (``SQLALCHEMY_DATABASE_URI``). After each deployment,
it runs ``python -m tests.preview_seed`` to list the fixture accounts in the
pull request comment.
"""

import pytest
from sqlalchemy.orm import selectinload

import collectives
from collectives.models import User
from tests.fixtures.user import PASSWORD

FIXTURE_MAIL_DOMAIN = "@example.org"
"""Domain of the mail addresses of the fixture users.

:type: string"""

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


def accounts_table() -> str:
    """Lists the fixture accounts, with their roles and badges.

    :returns: a Markdown table, in French as it is shown in the pull request.
    """
    users = (
        User.query.filter(User.mail.endswith(FIXTURE_MAIL_DOMAIN))
        .options(selectinload(User.roles), selectinload(User.badges))
        .order_by(User.license)
    )
    lines = [
        f"Comptes de test, mot de passe `{PASSWORD}` :",
        "",
        "| Identifiant | Nom | Profil |",
        "|---|---|---|",
    ]
    for user in users:
        profile = [
            f"{role.name} ({role.activity_type.name})"
            if role.activity_type
            else role.name
            for role in user.roles
        ]
        profile += [
            f"{badge.badge_id.display_name()} (expiré)"
            if badge.is_expired()
            else badge.badge_id.display_name()
            for badge in user.badges
        ]
        if user.is_youth():
            profile.append("Jeune")
        if user.is_minor():
            profile.append("Mineur")
        lines.append(
            f"| `{user.mail}` | {user.full_name()} | {', '.join(profile) or 'Adhérent'} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    with collectives.create_app().app_context():
        print(accounts_table())
