"""Fills the database of a pull request preview with realistic demo data.

Not part of the test suite: ``deployment/preview/collectives-preview`` runs
``pytest tests/preview_seed.py`` in the preview container, once, against the
database of the instance (``SQLALCHEMY_DATABASE_URI``), then
``python -m tests.preview_seed`` to list the fixture accounts for the pull
request comment.

The fixtures come from ``tests/fixtures/`` (one user/event per basic case) and
from ``tests/fixtures/preview.py`` (a realistic catalogue: more roles, badges,
events, registrations, payments, groups, uploads).
"""

from datetime import date

import pytest
from sqlalchemy.orm import selectinload

import collectives
from collectives.models import Configuration, Role, RoleIds, User, UserType, db
from collectives.utils import init
from tests.fixtures.user import PASSWORD

# pylint: disable=unused-argument, redefined-outer-name, protected-access
# pylint: disable=too-many-arguments, too-many-positional-arguments


@pytest.fixture
def app():
    """The application on the database of the instance, emptied first.

    Overrides the test fixture, which uses the test configuration. Like it,
    recreates the tables and the initial values, so that a seed that failed
    halfway can be run again."""
    preview_app = collectives.create_app()
    with preview_app.app_context():
        db.drop_all()
        db.create_all()
        init.populate_db(preview_app)
        # Values cached by create_app() before drop_all().
        with Configuration._lock:
            Configuration._cache.clear()
        yield preview_app


def enable_preview_modules() -> None:
    """Enables the optional modules so that the preview shows them.

    ``PAYMENT_ENABLED`` is set to Payline with an empty merchant id: online
    payments cannot complete without real credentials, but the payment pages
    and offline payments work.
    """
    values = {
        "ENABLE_SANCTIONS": True,
        "RETEX_ENABLED": True,
        "WHATSAPP_GROUPS_ENABLED": True,
        "PAYMENT_ENABLED": "Payline",
    }
    for name, value in values.items():
        item = Configuration.get_item(name)
        item.content = value
        Configuration.uncache(name)
    db.session.commit()


def test_seed(preview_seed_data):  # pylint: disable=unused-argument
    """Creates users of each role and events of each kind, with registrations,
    then enables the optional modules."""
    enable_preview_modules()


def accounts_table() -> str:
    """Lists the fixture accounts shown in the pull request comment.

    One account per profile: several fixtures share the same profile (e.g.
    the ten plain members), listing them all would be noise in the comment.
    The administrator account is given separately in the comment.

    :returns: a Markdown table, in French as it is shown in the pull request.
    """
    # The admin account is created with the Test type too.
    users = (
        User.query.filter(
            User.type == UserType.Test,
            ~User.roles.any(Role.role_id == RoleIds.Administrator),
        )
        .options(selectinload(User.roles), selectinload(User.badges))
        .order_by(User.license)
    )
    lines = [
        f"Comptes de test, mot de passe `{PASSWORD}` :",
        "",
        "| Identifiant | Nom | Profil |",
        "|---|---|---|",
    ]
    profiles = set()
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
        if user.license_expiry_date and user.license_expiry_date <= date.today():
            profile.append("Licence expirée")
        profile_text = ", ".join(profile) or "Adhérent"
        if profile_text in profiles:
            continue
        profiles.add(profile_text)
        lines.append(f"| `{user.mail}` | {user.full_name()} | {profile_text} |")
    return "\n".join(lines)


if __name__ == "__main__":
    with collectives.create_app().app_context():
        print(accounts_table())
