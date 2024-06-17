"""Unit tests for Role class"""

from collectives.models.role import RoleIds, Role
from collectives.models.user import User, activity_supervisors
from collectives.models.activity_type import ActivityType
from collectives.models import db

from tests.fixtures.user import promote_to_leader, promote_user


def test_add_role(user1: User, user2: User):
    """Test adding a general role to an user"""
    admin_role = Role(role_id=int(RoleIds.Administrator))
    user1.roles.append(admin_role)

    db.session.add(user1)
    db.session.commit()

    retrieved_user = User.query.filter_by(id=user1.id).first()
    assert len(retrieved_user.roles) == 1
    assert retrieved_user.is_admin()
    assert retrieved_user.is_moderator()
    assert not retrieved_user.can_lead_activity(ActivityType.get_all_types()[0])

    # Staff user: not a leader, but can create events without activity
    staff_role = Role(role_id=int(RoleIds.Staff))
    user2.roles.append(staff_role)
    assert not user2.is_leader()
    assert user2.can_create_events()
    assert not user2.get_organizable_activities()


def test_add_activity_role(user2: User, user3: User):
    """Test adding an activity-specific role to an user"""

    activity1 = db.session.get(ActivityType, 1)
    activity2 = db.session.get(ActivityType, 2)

    promote_to_leader(user2, activity=activity1.name)

    retrieved_user = User.query.filter_by(id=user2.id).first()
    assert len(retrieved_user.roles) == 1
    assert not retrieved_user.is_admin()
    assert not retrieved_user.is_moderator()
    assert retrieved_user.can_lead_activity(activity1)
    assert not retrieved_user.can_lead_activity(activity2)

    promote_user(
        user2, activity_name=activity2.name, role_id=RoleIds.ActivitySupervisor
    )

    supervisors = activity_supervisors([activity1])
    assert len(supervisors) == 0
    supervisors = activity_supervisors([activity2])
    assert len(supervisors) == 1
    supervisors = activity_supervisors([activity1, activity2])
    assert len(supervisors) == 1

    # Activity staff user: not a leader, but can create events of this activity
    promote_user(user3, activity_name=activity2.name, role_id=RoleIds.ActivityStaff)
    assert not user3.is_leader()
    assert user3.can_create_events()
    assert activity2 in user3.get_organizable_activities()
