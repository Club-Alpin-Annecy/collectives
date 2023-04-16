"""Unit tests for UserGroup class"""

from collectives.models.user_group import (
    UserGroup,
    GroupEventCondition,
    GroupLicenseCondition,
    GroupRoleCondition,
)
from collectives.models import db, RoleIds, RegistrationStatus


# pylint: disable=R0915
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def test_user_group_members(
    event1_with_reg, user1, user2, president_user, admin_user, supervisor_user
):
    """Test listing user group members"""

    user2_reg = [reg for reg in event1_with_reg.registrations if reg.user == user2][0]
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
    assert admin_user in group0_members
    assert president_user not in group0_members

    gec.is_leader = False
    db.session.add(gec)
    db.session.commit()

    group0_members = group0.get_members()
    assert len(group0_members) == 3
    assert user1 in group0_members
    assert admin_user not in group0_members

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
    assert admin_user not in group0_members

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
