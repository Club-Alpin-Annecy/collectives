"""Unit tests for UserGroup class"""

from collectives.models import User, BadgeIds, RegistrationStatus, RoleIds, db
from collectives.models.user_group import (
    GroupBadgeCondition,
    GroupEventCondition,
    GroupLicenseCondition,
    GroupRoleCondition,
    UserGroup,
)
from collectives.utils.time import current_time


# pylint: disable=R0915
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=too-many-locals
def test_user_group_members(
    event1_with_reg,
    user1,
    user2,
    president_user,
    leader_user,
    supervisor_user,
):
    """Test listing user group members"""

    user2_reg = next(reg for reg in event1_with_reg.registrations if reg.user == user2)
    user2_reg.status = RegistrationStatus.Waiting
    db.session.add(user2_reg)

    group0 = UserGroup()

    # Test event conditions
    gec = GroupEventCondition(event_id=event1_with_reg.id)
    db.session.add(gec)

    group0.event_conditions.append(gec)
    db.session.add(group0)
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 4
    assert user1 in group0_members
    assert user2 not in group0_members
    assert leader_user in group0_members
    assert president_user not in group0_members

    gec.is_leader = False
    db.session.add(gec)
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 3
    assert user1 in group0_members
    assert leader_user not in group0_members

    gec.is_leader = None
    db.session.add(gec)
    db.session.commit()

    group0.event_conditions.clear()
    db.session.delete(gec)
    db.session.commit()

    # Test role conditions
    grc1 = GroupRoleCondition(role_id=RoleIds.President)
    grc2 = GroupRoleCondition(
        role_id=RoleIds.ActivitySupervisor,
        activity_id=supervisor_user.get_supervised_activities()[0].id,
    )
    group0.role_conditions.append(grc1)
    group0.role_conditions.append(grc2)

    db.session.add(group0)
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 2
    assert supervisor_user in group0_members
    assert president_user in group0_members
    assert leader_user not in group0_members

    grc2.activity_id += 1
    db.session.add(grc2)
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 1
    assert supervisor_user not in group0_members
    assert president_user in group0_members

    group0.role_conditions.clear()
    db.session.delete(grc1)
    db.session.delete(grc2)
    db.session.commit()

    # Test license conditions
    user1.license_category = "J1"
    president_user.license_category = "J2"

    glc1 = GroupLicenseCondition(license_category="J1")
    glc2 = GroupLicenseCondition(license_category="J2")
    group0.license_conditions.append(glc1)
    group0.license_conditions.append(glc2)

    db.session.add(group0)
    db.session.add(user1)
    db.session.add(president_user)
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 2
    assert supervisor_user not in group0_members
    assert president_user in group0_members
    assert user1 in group0_members

    # Test combination
    grc1 = GroupRoleCondition(role_id=RoleIds.President)
    group0.role_conditions.append(grc1)
    db.session.add(group0)
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 1
    assert president_user in group0_members

    gec = GroupEventCondition(event_id=event1_with_reg.id)
    group0.event_conditions.append(gec)
    db.session.add(group0)
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 0

    # Test negation
    gec.invert = True
    db.session.add(gec)
    db.session.commit()
    group0_members = group0.get_members()
    assert len(group0_members) == 1
    assert president_user in group0_members

    group0.badge_conditions.clear()
    group0.role_conditions.clear()
    group0.event_conditions.clear()
    for cond in group0.license_conditions:
        cond.invert = True
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 5
    assert president_user not in group0_members
    assert user1 not in group0_members


def test_badge_user_group_members(
    user_with_expired_benevole_badge,
    user_with_valid_benevole_badge,
    user_with_valid_suspended_badge,
):
    """Test listing user group members with bagde conditions"""

    time = current_time()
    group0 = UserGroup()

    # Test event conditions
    grc = GroupBadgeCondition(badge_id=BadgeIds.Benevole)
    db.session.add(grc)

    group0.badge_conditions.append(grc)
    db.session.add(group0)
    db.session.commit()

    group0_members = group0.get_members(time=time)
    assert len(group0_members) == 1
    assert user_with_valid_benevole_badge in group0_members

    grc.invert = True
    db.session.commit()

    group0_members = group0.get_members(time=time)
    assert len(group0_members) >= 2
    assert user_with_valid_benevole_badge not in group0_members

    grc.invert = False
    grc.badge_id = None
    db.session.commit()

    group0_members = group0.get_members(time=time)
    assert len(group0_members) == 2
    assert user_with_valid_benevole_badge in group0_members
    assert user_with_valid_suspended_badge in group0_members
    assert user_with_expired_benevole_badge not in group0_members


def test_badge_level_user_group_members(
    user1: User,
    user_with_practitioner_badge: User,
    user_with_skill_badge: User,
):
    """Test listing user group members with bagde conditions and levels"""

    group0 = UserGroup()

    # Test event conditions
    user_level  = user_with_practitioner_badge.get_most_relevant_competency_badge(
        BadgeIds.Practitioner
    ).level
    grc = GroupBadgeCondition(badge_id=BadgeIds.Practitioner, level=user_level)
    db.session.add(grc)

    group0.badge_conditions.append(grc)
    db.session.add(group0)
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 1
    assert user_with_practitioner_badge in group0_members


    grc.level += 1
    db.session.add(grc)
    db.session.commit() 
    group0_members = group0.get_members()
    assert len(group0_members) == 0


    grc.level = user_with_skill_badge.get_most_relevant_competency_badge(
        BadgeIds.Skill
    ).level
    grc.badge_id = BadgeIds.Skill
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 1
    assert user_with_skill_badge in group0_members


def test_any_role_condition(user1, president_user, leader_user):
    """Test "any role" group condition"""

    group0 = UserGroup()

    any_role_condition = GroupRoleCondition()
    group0.role_conditions.append(any_role_condition)

    db.session.add(group0)
    db.session.commit()

    group0_members = group0.get_members()
    assert user1 not in group0_members
    assert president_user in group0_members
    assert leader_user in group0_members
