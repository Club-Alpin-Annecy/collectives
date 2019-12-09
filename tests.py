import unittest
import flask_testing
import datetime

from collectives import create_app 
from collectives.models import db, User, ActivityType, Role, RoleIds, Event, Registration, RegistrationLevels, RegistrationStatus


def create_test_user(email="test", license=""):
    user = User(mail=email, first_name="Test", last_name="Test", password="",
                license = license, enabled =True, phone="")
    db.session.add(user)
    db.session.commit()
    return user

def create_test_activity(name="Ski"):
    activity = ActivityType(name=name, short="")
    db.session.add(activity)
    db.session.commit()
    return activity

class ModelTest(flask_testing.TestCase):

    def create_app(self):

        # pass in test configuration
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/testdb.sqlite"
        app.config['TESTING'] = True
        return app

    def setUp(self):

        db.create_all()

    def tearDown(self):

        db.session.remove()
        db.drop_all()

class TestUsers(ModelTest):

    def test_create_user(self):
        user = create_test_user()   
        assert user in db.session

class TestActivities(ModelTest):

    def test_create_activity(self):
        activity = create_test_activity()   
        assert activity in db.session

class TestRoles(ModelTest):

    def make_role(self, user):
        return Role(user = user, role_id = int(RoleIds.Administrator))
    
    def make_activity_role(self, user, activity):
        return Role(user = user, activity_id = activity.id, role_id = int(RoleIds.EventLeader))

    def commit_role(self, role):
        db.session.add(role)
        db.session.commit()

    def test_add_role(self):
        user = create_test_user()

        role = self.make_role(user)
        user.roles.append(role)
 
        db.session.commit()

        assert role in db.session

        retrieved_user = User.query.filter_by(id = user.id).first()
        assert len(retrieved_user.roles) == 1
        assert retrieved_user.is_admin()
        assert retrieved_user.is_moderator()
        assert not retrieved_user.can_lead_activity(0)

    def test_add_activity_role(self):
        user = create_test_user()
        activity1 = create_test_activity("1")
        activity2 = create_test_activity("2")

        role = self.make_activity_role(user, activity1)
        user.roles.append(role)
 
        db.session.commit()

        assert role in db.session

        retrieved_user = User.query.filter_by(id = user.id).first()
        assert len(retrieved_user.roles) == 1
        assert not retrieved_user.is_admin()
        assert not retrieved_user.is_moderator()
        assert retrieved_user.can_lead_activity(activity1.id)
        assert not retrieved_user.can_lead_activity(activity2.id)

class TestEvents(TestUsers):
    
    def make_event(self):
        return Event(title="Event", description="", shortdescription="",
                    num_slots=2, num_online_slots=1, 
                    start=datetime.datetime.now() + datetime.timedelta(days=1), 
                    end=datetime.date.today() + datetime.timedelta(days=1),
                    registration_open_time = datetime.datetime.now(), 
                    registration_close_time = datetime.datetime.now() + datetime.timedelta(days=1), 
                    )
    
    def test_add_event(self):
        event = self.make_event()
        db.session.add(event)
        db.session.commit()
        return event

    def test_event_validity(self):
        user1 = create_test_user("email1", "license1")
        user2 = create_test_user("email2", "license2")
        activity1 = create_test_activity("1")
        activity2 = create_test_activity("2")

        user1.roles.append(Role(role_id=RoleIds.EventLeader, activity_id=activity1.id))
        user2.roles.append(Role(role_id=RoleIds.EventLeader, activity_id=activity2.id))
        db.session.commit()

        event = self.make_event()
        # Event has no activity, not valid
        assert not event.is_valid()

        # Test leaders
        event.activity_types.append(activity1)
        assert not event.has_valid_leaders()
        event.leaders.append(user1)
        assert event.has_valid_leaders()

        event.activity_types.append(activity2)
        assert not event.has_valid_leaders()
        event.leaders.append(user2)
        assert event.has_valid_leaders()

        assert event.is_valid()

        # Test slots
        event.num_slots=0
        assert not event.is_valid()
        event.num_online_slots=0
        assert event.is_valid()
        event.num_slots=-1
        assert not event.is_valid()
        event.num_slots=0
        assert event.is_valid()

        # Test dates
        event.end = datetime.date.today()
        assert not event.is_valid()
        event.end = event.start.date()
        assert event.is_valid()

        assert event.is_registration_open_at_time(datetime.datetime.now())

        event.registration_open_time = event.registration_close_time + datetime.timedelta(hours=1)
        assert not event.opens_before_closes()
        assert not event.is_valid()

        event.registration_open_time = datetime.datetime.combine(event.end, datetime.datetime.min.time()) + datetime.timedelta(days=1)
        event.registration_close_time = event.registration_open_time + datetime.timedelta(hours=1)
        assert event.opens_before_closes()
        assert not event.opens_before_ends()
        assert not event.is_valid()
        
        assert not event.is_registration_open_at_time(datetime.datetime.now())

class TestRegistrations(TestEvents):
    
    def make_registration(self, user):
        now = datetime.datetime.timestamp(datetime.datetime.now())
        return Registration(user=user, status=RegistrationStatus.Active, level=RegistrationLevels.Normal)

    def test_add_registration(self):
        event = self.make_event()
        event.num_online_slots = 2
        db.session.add(event)
        db.session.commit()
        
        now = datetime.datetime.now()
        assert event.is_registration_open_at_time(now)
        assert event.has_free_slots()

        user1 = create_test_user("email1", "license1")
        user2 = create_test_user("email2", "license2")

        assert event.can_self_register(user1, now)
        assert event.can_self_register(user2, now)

        event.registrations.append(self.make_registration(user1))
        db.session.commit()
        assert not event.can_self_register(user1, now)
        assert event.can_self_register(user2, now)

        event.num_online_slots = 1

        assert not event.has_free_slots()
        assert not event.can_self_register(user2, now)

        event.registrations[0].status=RegistrationStatus.Rejected
        assert event.has_free_slots()
        assert not event.can_self_register(user1, now)
        assert event.can_self_register(user2, now)

        db.session.commit()

        # Test db has been updated
        db_event = Event.query.filter_by(id = event.id).first()
        assert db_event.has_free_slots()
        assert not db_event.can_self_register(user1, now)
        assert db_event.can_self_register(user2, now)


if __name__ == '__main__':
    unittest.main()