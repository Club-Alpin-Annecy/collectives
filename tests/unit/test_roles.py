from collectives.models.role import RoleIds, Role
from collectives.models.user import User, activity_supervisors
from collectives.models.activity_type import ActivityType
from collectives.models import db

from tests.fixtures.user import promote_to_leader, promote_user


def test_add_role(user1):
    """Test adding a general role to an user"""
    admin_role = Role(role_id=int(RoleIds.Administrator))
    user1.roles.append(admin_role)

    db.session.add(user1)
    db.session.commit()

    assert admin_role in db.session

    retrieved_user = User.query.filter_by(id=user1.id).first()
    assert len(retrieved_user.roles) == 1
    assert retrieved_user.is_admin()
    assert retrieved_user.is_moderator()
    assert not retrieved_user.can_lead_activity(0)


def test_add_activity_role(user2):
    """Test adding an activity-specific role to an user"""

    activity1 = ActivityType.query.get(1)
    activity2 = ActivityType.query.get(2)

    promote_to_leader(user2, activity=activity1.name)

    retrieved_user = User.query.filter_by(id=user2.id).first()
    assert len(retrieved_user.roles) == 1
    assert not retrieved_user.is_admin()
    assert not retrieved_user.is_moderator()
    assert retrieved_user.can_lead_activity(activity1.id)
    assert not retrieved_user.can_lead_activity(activity2.id)

    promote_user(
        user2, activity_name=activity2.name, role_id=RoleIds.ActivitySupervisor
    )

    supervisors = activity_supervisors([activity1])
    assert len(supervisors) == 0
    supervisors = activity_supervisors([activity2])
    assert len(supervisors) == 1
    supervisors = activity_supervisors([activity1, activity2])
    assert len(supervisors) == 1
