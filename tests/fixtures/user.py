""" Module to create fixture users. """

from functools import wraps
from datetime import date, datetime, timedelta

import pytest

from collectives.models import User, Gender, db, Role, RoleIds, ActivityType
from collectives.models import Badge, BadgeIds, UserType

# pylint: disable=unused-argument,redefined-outer-name, unused-import

from tests.fixtures.app import enable_sanctions
from tests.mock.extranet import VALID_LICENSE


PASSWORD = "fooBar2+!"
""" Default test password for non admin users.

:type: string
"""

# pylint: disable=invalid-name, global-statement
_id_seed = 0
""" A unique identifier number for fixture users. It is not the
    user id. It determines the user license number.
"""


def _next_id_seed() -> int:
    """Generates a new unique identifier"""
    global _id_seed
    _id_seed += 1
    return _id_seed


# pylint: enable=invalid-name, global-statement


def inject_fixture(name, names):
    """Create and add a new fixture user.

    :param string name: Fixture name.
    :param "(string,string)" names: First and lastname of the user.
    """
    globals()[name] = generate_user(names)


def generate_user(names):
    """Generate fixture users.

    :param int id: An identifiying integer for the user
    :param (string,string) names: first and last names for the user
    :returns: the newly created user
    :rtype: :py:class:`collectives.models.user.User`"""

    identifier = _next_id_seed()

    @wraps(identifier)
    @wraps(names)
    @pytest.fixture
    def user(app):
        """A Standard user"""

        print(names, identifier)

        user = User()
        user.first_name = names[0]
        user.last_name = names[1]
        user.gender = Gender.Unknown
        user.mail = f"user{identifier}@example.org"
        user.type = UserType.Test
        user.license = str(identifier + 990000000000)
        user.license_category = "XX"
        user.date_of_birth = date(2000, 1, identifier % 28 + 1)
        user.password = PASSWORD
        user.phone = f"0601020{identifier:03d}"
        user.emergency_contact_name = f"Emergency {identifier}"
        user.emergency_contact_phone = f"0699999{identifier:03}"
        user.legal_text_signature_date = datetime.now()
        user.legal_text_signed_version = 1
        user.gender = Gender(identifier % 2 + 1)

        db.session.add(user)
        db.session.commit()
        return user

    return user


USER_NAMES = [
    ("Jan", "Johnston"),
    ("Evan", "Walsh"),
    ("Kimberly", "Paterson"),
    ("Jake", "Marshall"),
    ("Boris", "Bailey"),
    ("Frank", "Morgan"),
    ("Chloe", "White"),
    ("Michael", "Davidson"),
    ("Theresa", "Bailey"),
    ("Jake", "Piper"),
]
""" Basic list of names.

:type: list()"""
for i, user_name in enumerate(USER_NAMES):
    inject_fixture(f"user{i+1}", user_name)


@pytest.fixture
def admin_user(app):
    """:returns: The admin user."""
    return db.session.get(User, 1)


inject_fixture("prototype_leader_user", ("Romeo", "Capo"))


@pytest.fixture
def leader_user(prototype_leader_user):
    """:returns: An Alpinisme leader user."""
    promote_to_leader(prototype_leader_user)
    db.session.add(prototype_leader_user)
    db.session.commit()
    return prototype_leader_user


@pytest.fixture
def leader_user_with_event(leader_user, event1):
    """:returns: A leader User which leads event1"""
    event1.leaders.append(leader_user)
    event1.main_leader = leader_user
    db.session.add(leader_user)
    db.session.commit()
    return leader_user


inject_fixture("prototype_leader2_user", ("Evan", "Przewodnik"))


@pytest.fixture
def leader2_user(prototype_leader2_user):
    """:returns: An Alpinisme leader user."""
    promote_to_leader(prototype_leader2_user)
    db.session.add(prototype_leader2_user)
    db.session.commit()
    return prototype_leader2_user


@pytest.fixture
def leader2_user_with_event(leader2_user, event2):
    """:returns: A leader User which leads event2"""
    event2.leaders.append(leader2_user)
    event2.main_leader = leader2_user
    db.session.add(leader2_user)
    db.session.commit()
    return leader2_user


inject_fixture("prototype_president_user", ("Russ", "Guevara"))


@pytest.fixture
def president_user(prototype_president_user):
    """:returns: A user with a president role."""
    promote_user(prototype_president_user, RoleIds.President, None)
    db.session.add(prototype_president_user)
    db.session.commit()
    return prototype_president_user


inject_fixture("prototype_supervisor_user", ("Ted", "Fincher"))


@pytest.fixture
def supervisor_user(prototype_supervisor_user):
    """:returns: A user with an Alpinisme supervisor role."""
    promote_user(prototype_supervisor_user, RoleIds.ActivitySupervisor)
    db.session.add(prototype_supervisor_user)
    db.session.commit()
    return prototype_supervisor_user


inject_fixture("prototype_hotline_user", ("Bill", "Hatch"))


@pytest.fixture
def hotline_user(prototype_hotline_user):
    """:returns: A user with a hotline role."""
    promote_user(prototype_hotline_user, RoleIds.Hotline)
    db.session.add(prototype_hotline_user)
    db.session.commit()
    return prototype_hotline_user


inject_fixture("prototype_youth_user", ("Young", "Climber"))


@pytest.fixture
def youth_user(prototype_youth_user: User):
    """:returns: A user with a youth license."""
    prototype_youth_user.license_category = "J1"
    db.session.add(prototype_youth_user)
    db.session.commit()
    return prototype_youth_user


inject_fixture("prototype_user_with_valid_benevole_badge", ("Good", "Girl"))


@pytest.fixture
def user_with_valid_benevole_badge(prototype_user_with_valid_benevole_badge: User):
    """:returns: A user with a valid benevole Badge."""
    add_benevole_badge_to_user(prototype_user_with_valid_benevole_badge)
    db.session.add(prototype_user_with_valid_benevole_badge)
    db.session.commit()
    return prototype_user_with_valid_benevole_badge


inject_fixture(
    "prototype_user_with_expired_benevole_badge", ("Boy", "WhoShoulContribute")
)


@pytest.fixture
def user_with_expired_benevole_badge(prototype_user_with_expired_benevole_badge: User):
    """:returns: A user with an expired benevole Badge."""
    add_benevole_badge_to_user(
        prototype_user_with_expired_benevole_badge, date.today() - timedelta(days=65)
    )
    db.session.add(prototype_user_with_expired_benevole_badge)
    db.session.commit()
    return prototype_user_with_expired_benevole_badge


inject_fixture("prototype_extranet_user", ("Extranet", "User"))


@pytest.fixture
def extranet_user(prototype_extranet_user):
    """:returns: A user with type extranet."""
    prototype_extranet_user.type = UserType.Extranet
    prototype_extranet_user.license = VALID_LICENSE
    prototype_extranet_user.license_expiry_date = date.today() + timedelta(days=365)

    db.session.add(prototype_extranet_user)
    db.session.commit()
    return prototype_extranet_user


def promote_to_leader(user, activity="Alpinisme"):
    """Add a leader role to a user.

    :param User user: the user to be promoted
    :param string activity: Activity name to which user will be promoted. Defaul Alpinisme
    """
    promote_user(user, RoleIds.EventLeader, activity)


def promote_user(
    user, role_id, activity_name="Alpinisme", confidentiality_agreement_signature=True
):
    """Manage to add a role to a user

    :param User user: the user to promote
    :param RoleIds role_id: the type of user to add
    :param string activity_name: The activity name for the role. Default Alpinisme
    :param bool confidentiality_agreement_signature: If method should sign the
        confidentiality agreement for the user.
    """
    role = Role()
    role.user_id = user.id
    role.role_id = role_id
    if activity_name:
        activity_type = ActivityType.query.filter_by(name=activity_name).first()
        role.activity_id = activity_type.id
    if confidentiality_agreement_signature:
        user.confidentiality_agreement_signature_date = datetime.now()
    db.session.add(role)


def add_benevole_badge_to_user(
    user,
    expiration_date=(date.today() + timedelta(days=365)),
    badge_id=int(BadgeIds.Benevole),
    activity_name="Alpinisme",
):
    """Manage to add a badge to a user

    :param User user: the user to add a badge to
    :expiration_date: the expiration date of the badge (Default is today + 1 year, so a valid one)
    :param badgeIds badge_id: the type of badge to add
    :param string activity_name: The activity name for the role. Default Alpinisme
    """
    badge = Badge()
    badge.user_id = user.id
    badge.badge_id = badge_id
    badge.expiration_date = expiration_date
    if activity_name:
        activity_type = ActivityType.query.filter_by(name=activity_name).first()
        badge.activity_id = activity_type.id
    db.session.add(badge)


# Users with badges related to late unregistration
def add_badge_to_user(
    user,
    badge_id,
    level=1,
    expiration_date=(date.today() + timedelta(days=365)),
    activity_name="Alpinisme",
):
    """Manage to add a badge to a user

    :param User user: the user to add a badge to
    :expiration_date: the expiration date of the badge (Default is today + 1 year, so a valid one)
    :param badgeIds badge_id: the type of badge to add
    :param string activity_name: The activity name for the role. Default Alpinisme
    """
    badge = Badge()
    badge.user_id = user.id
    badge.badge_id = badge_id
    badge.level = level
    badge.expiration_date = expiration_date
    if activity_name:
        activity_type = ActivityType.query.filter_by(name=activity_name).first()
        badge.activity_id = activity_type.id
    db.session.add(badge)


inject_fixture("prototype_user_with_valid_first_warning_badge", ("Anakin", "Skywalker"))


@pytest.fixture
def user_with_valid_first_warning_badge(
    prototype_user_with_valid_first_warning_badge: User, enable_sanctions
):
    """:returns: A user with a valid first warning Badge."""
    add_badge_to_user(
        prototype_user_with_valid_first_warning_badge,
        BadgeIds.UnjustifiedAbsenceWarning,
        expiration_date=date.today() + timedelta(days=60),
    )
    db.session.add(prototype_user_with_valid_first_warning_badge)
    db.session.commit()
    return prototype_user_with_valid_first_warning_badge


inject_fixture("prototype_user_with_expired_first_warning_badge", ("Obi-Wan", "Kenobi"))


@pytest.fixture
def user_with_expired_first_warning_badge(
    prototype_user_with_expired_first_warning_badge: User,
    enable_sanctions,
):
    """:returns: A user with an expired first warning Badge."""
    add_badge_to_user(
        prototype_user_with_expired_first_warning_badge,
        BadgeIds.UnjustifiedAbsenceWarning,
        expiration_date=date.today() - timedelta(days=3),
    )
    db.session.add(prototype_user_with_expired_first_warning_badge)
    db.session.commit()
    return prototype_user_with_expired_first_warning_badge


inject_fixture("prototype_user_with_valid_second_warning_badge", ("Han", "Solo"))


@pytest.fixture
def user_with_valid_second_warning_badge(
    prototype_user_with_valid_second_warning_badge: User,
    enable_sanctions,
):
    """:returns: A user with a valid second warning Badge."""
    add_badge_to_user(
        prototype_user_with_valid_second_warning_badge,
        BadgeIds.UnjustifiedAbsenceWarning,
        expiration_date=date.today() + timedelta(days=60),
    )
    add_badge_to_user(
        prototype_user_with_valid_second_warning_badge,
        BadgeIds.UnjustifiedAbsenceWarning,
        2,
        expiration_date=date.today() + timedelta(days=60),
    )
    db.session.add(prototype_user_with_valid_second_warning_badge)
    db.session.commit()
    return prototype_user_with_valid_second_warning_badge


inject_fixture("prototype_user_with_expired_second_warning_badge", ("Leia", "Organa"))


@pytest.fixture
def user_with_expired_second_warning_badge(
    prototype_user_with_expired_second_warning_badge: User,
    enable_sanctions,
):
    """:returns: A user with an expired second warning Badge."""
    add_badge_to_user(
        prototype_user_with_expired_second_warning_badge,
        BadgeIds.UnjustifiedAbsenceWarning,
        expiration_date=date.today() + timedelta(days=30),
    )
    add_badge_to_user(
        prototype_user_with_expired_second_warning_badge,
        BadgeIds.UnjustifiedAbsenceWarning,
        2,
        expiration_date=date.today() - timedelta(days=3),
    )
    db.session.add(prototype_user_with_expired_second_warning_badge)
    db.session.commit()
    return prototype_user_with_expired_second_warning_badge


inject_fixture(
    "prototype_user_with_valid_suspended_badge", ("Chewbacca", "The Wookiee")
)


@pytest.fixture
def user_with_valid_suspended_badge(
    prototype_user_with_valid_suspended_badge: User, enable_sanctions
):
    """:returns: A user with a valid suspended Badge."""
    add_badge_to_user(
        prototype_user_with_valid_suspended_badge,
        BadgeIds.Suspended,
        expiration_date=date.today() + timedelta(days=60),
    )
    db.session.add(prototype_user_with_valid_suspended_badge)
    db.session.commit()
    return prototype_user_with_valid_suspended_badge


inject_fixture("prototype_user_with_expired_suspended_badge", ("Darth", "Vader"))


@pytest.fixture
def user_with_expired_suspended_badge(
    prototype_user_with_expired_suspended_badge: User,
    enable_sanctions,
):
    """:returns: A user with an expired suspended Badge."""
    add_badge_to_user(
        prototype_user_with_expired_suspended_badge,
        BadgeIds.Suspended,
        expiration_date=date.today() - timedelta(days=3),
    )
    db.session.add(prototype_user_with_expired_suspended_badge)
    db.session.commit()
    return prototype_user_with_expired_suspended_badge


inject_fixture("user_with_no_warning_badge", ("Jabba", "The Hutt"))
