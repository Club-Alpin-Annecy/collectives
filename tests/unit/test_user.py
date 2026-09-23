"""Module to test User model properties."""

from datetime import date

from dateutil.relativedelta import relativedelta

from collectives.models import User, UserType, db

# pylint: disable=unused-argument


def test_is_active_sql_matches_python(user1: User):
    """The SQL expression of is_active must agree with the Python property.

    Regression test: the ``case`` used to be written with ``value=cls.type``,
    whose enum keys were never rendered the way the column stores them. No branch
    ever matched, ``else_`` applied, and every account looked active in SQL —
    expired licences included. Any query filtering on ``User.is_active`` silently
    returned wrong rows.
    """
    user1.type = UserType.Extranet
    user1.license_expiry_date = date.today() - relativedelta(days=1)
    db.session.commit()

    assert not user1.is_active
    assert user1 not in User.query.filter(User.is_active).all()
    assert user1 in User.query.filter(~User.is_active).all()


def test_is_active_sql_keeps_valid_licence(user1: User):
    """A valid licence stays active, both in Python and in SQL."""
    user1.type = UserType.Extranet
    user1.license_expiry_date = date.today() + relativedelta(years=1)
    db.session.commit()

    assert user1.is_active
    assert user1 in User.query.filter(User.is_active).all()


def test_is_active_sql_excludes_unverified(user1: User):
    """An unverified local account is inactive in SQL too."""
    user1.type = UserType.UnverifiedLocal
    db.session.commit()

    assert not user1.is_active
    assert user1 in User.query.filter(~User.is_active).all()


def test_is_active_sql_excludes_disabled(user1: User):
    """A disabled account is inactive whatever its type."""
    user1.enabled = False
    db.session.commit()

    assert not user1.is_active
    assert user1 in User.query.filter(~User.is_active).all()
