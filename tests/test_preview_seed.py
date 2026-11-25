"""Smoke tests for the seed of pull request previews (``tests/preview_seed.py``).

``preview_seed.py`` itself is not collected by the test suite (not a
``test_*.py``); these tests run its fixtures in CI to make sure the seed keeps
working and keeps filling a preview with a realistic volume of data.
"""

# pylint: disable=unused-argument, redefined-outer-name

from collectives.models import (
    Configuration,
    Event,
    Payment,
    Registration,
    Retex,
    User,
    UserGroup,
    db,
)
from tests.preview_seed import accounts_table, enable_modules

# ``preview_seed_data`` comes from tests.fixtures.preview, registered in
# pytest_plugins: requesting it here runs the whole preview seed.


def test_seed_fills_the_database(preview_seed_data):
    """The seed creates enough users, events, registrations and payments."""
    enable_modules()
    assert User.query.count() >= 25
    # More events than the page size of the event list (25), so that the
    # pagination of a preview is visible.
    assert Event.query.count() >= 25
    assert Registration.query.count() >= 20
    assert UserGroup.query.count() >= 3
    assert Payment.query.count() >= 4
    assert Retex.query.count() >= 1


def test_accounts_table_lists_one_account_per_profile(preview_seed_data):
    """One row per profile: no duplicated plain-member rows."""
    rows = [line for line in accounts_table().splitlines() if line.startswith("| `")]
    assert len(rows) >= 8
    profiles = [line.split("|")[3].strip() for line in rows]
    assert len(profiles) == len(set(profiles))


def test_enable_modules(app):
    """The optional modules are enabled, except those needing a third party."""
    assert not Configuration.WHATSAPP_GROUPS_ENABLED
    assert not Configuration.RETEX_ENABLED

    enabled = enable_modules()

    assert Configuration.WHATSAPP_GROUPS_ENABLED
    assert Configuration.RETEX_ENABLED
    assert Configuration.ENABLE_SANCTIONS
    assert Configuration.HELLOASSO_SANDBOX
    assert not Configuration.LOXYA_ENABLED
    assert "LOXYA_ENABLED" not in enabled
    # Booleans that are not module switches keep their value.
    assert not Configuration.LEADER_PRIVACY
    assert "LEADER_PRIVACY" not in enabled
