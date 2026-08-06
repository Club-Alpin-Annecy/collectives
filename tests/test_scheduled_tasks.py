"""Module to test periodic maintenance tasks."""

# pylint: disable=unused-argument

from datetime import date

from dateutil.relativedelta import relativedelta

from collectives.models import Configuration, User, db
from collectives.utils.misc import purge_expired_accounts


def test_purge_expired_accounts_anonymizes_old_license(user1: User):
    """A user whose license expired more than the retention period ago is anonymized."""
    user1.license_expiry_date = date.today() - relativedelta(
        years=Configuration.ACCOUNT_RETENTION_YEARS, days=1
    )
    db.session.commit()

    count = purge_expired_accounts()

    assert count == 1
    assert not user1.enabled
    assert user1.first_name == "Compte"
    assert user1.license == str(user1.id)
    assert "localhost" in user1.mail


def test_purge_expired_accounts_keeps_recent_license(user1: User):
    """A user whose license expired less than the retention period ago is untouched."""
    user1.license_expiry_date = date.today() - relativedelta(
        years=Configuration.ACCOUNT_RETENTION_YEARS, days=-1
    )
    db.session.commit()

    count = purge_expired_accounts()

    assert count == 0
    assert user1.enabled
    assert user1.first_name != "Compte"


def test_purge_expired_accounts_ignores_users_without_expiry(user1: User):
    """A user without a license expiry date (e.g. Local/Test account) is untouched."""
    user1.license_expiry_date = None
    db.session.commit()

    count = purge_expired_accounts()

    assert count == 0
    assert user1.enabled


def test_purge_expired_accounts_is_idempotent(user1: User):
    """Running the purge twice does not reprocess already-anonymized accounts."""
    user1.license_expiry_date = date.today() - relativedelta(
        years=Configuration.ACCOUNT_RETENTION_YEARS, days=1
    )
    db.session.commit()

    first_count = purge_expired_accounts()
    second_count = purge_expired_accounts()

    assert first_count == 1
    assert second_count == 0
