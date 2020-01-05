import unittest
import flask_testing
import datetime
from os import environ

# pylint: disable=C0301
from collectives import create_app
from collectives.models import db, User, ActivityType, Role, RoleIds, Event
from collectives.models import Registration, RegistrationLevels, RegistrationStatus
# pylint: enable=C0301
from collectives.api import find_users_by_fuzzy_name
from collectives.helpers import current_time
from collectives.utils.csv import fill_from_csv

from collectives import extranet

def create_test_user(email="test", user_license=""):
    user = User(mail=email, first_name="Test", last_name="Test", password="",
                license=user_license, enabled=True, phone="")
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
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///testdb.sqlite"
        app.config['TESTING'] = True
        app.config['EXTRANET_ACCOUNT_ID'] = None
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
        return Role(user=user, role_id=int(RoleIds.Administrator))

    def make_activity_role(self, user, activity):
        return Role(user=user,
                    activity_id=activity.id,
                    role_id=int(RoleIds.EventLeader))

    def commit_role(self, role):
        db.session.add(role)
        db.session.commit()

    def test_add_role(self):
        user = create_test_user()

        role = self.make_role(user)
        user.roles.append(role)

        db.session.commit()

        assert role in db.session

        retrieved_user = User.query.filter_by(id=user.id).first()
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

        retrieved_user = User.query.filter_by(id=user.id).first()
        assert len(retrieved_user.roles) == 1
        assert not retrieved_user.is_admin()
        assert not retrieved_user.is_moderator()
        assert retrieved_user.can_lead_activity(activity1.id)
        assert not retrieved_user.can_lead_activity(activity2.id)


class TestEvents(TestUsers):

    def make_event(self):
        return Event(title="Event",
                     description="",
                     shortdescription="",
                     num_slots=2, num_online_slots=1,
                     start=datetime.datetime.now() + datetime.timedelta(days=1),
                     end=datetime.datetime.now() + datetime.timedelta(days=2),
                     registration_open_time=datetime.datetime.now(),
                     registration_close_time=datetime.datetime.now() +
                     datetime.timedelta(days=1))

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

        user1.roles.append(Role(role_id=RoleIds.EventLeader,
                                activity_id=activity1.id))
        user2.roles.append(Role(role_id=RoleIds.EventLeader,
                                activity_id=activity2.id))
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
        event.num_slots = 0
        assert not event.is_valid()
        event.num_online_slots = 0
        assert event.is_valid()
        event.num_slots = -1
        assert not event.is_valid()
        event.num_slots = 0
        assert event.is_valid()

        # Test dates
        event.end = datetime.datetime.now()
        assert not event.is_valid()
        event.end = event.start
        assert event.is_valid()

        assert event.is_registration_open_at_time(datetime.datetime.now())

        event.registration_open_time = event.registration_close_time + \
            datetime.timedelta(hours=1)
        assert not event.opens_before_closes()
        assert not event.is_valid()

        event.registration_open_time = datetime.datetime.combine(
            event.end,
            datetime.datetime.min.time()) + datetime.timedelta(days=1)
        event.registration_close_time = event.registration_open_time + \
            datetime.timedelta(hours=1)
        assert event.opens_before_closes()
        assert not event.opens_before_ends()
        assert not event.is_valid()

        assert not event.is_registration_open_at_time(datetime.datetime.now())


class TestRegistrations(TestEvents):

    def make_registration(self, user):
        datetime.datetime.timestamp(datetime.datetime.now())
        return Registration(
            user=user,
            status=RegistrationStatus.Active,
            level=RegistrationLevels.Normal)

    def test_add_registration(self):
        event = self.make_event()
        event.num_online_slots = 2
        db.session.add(event)
        db.session.commit()

        now = datetime.datetime.now()
        assert event.is_registration_open_at_time(now)
        assert event.has_free_online_slots()

        user1 = create_test_user("email1", "license1")
        user2 = create_test_user("email2", "license2")

        assert event.can_self_register(user1, now)
        assert event.can_self_register(user2, now)

        event.registrations.append(self.make_registration(user1))
        db.session.commit()
        assert not event.can_self_register(user1, now)
        assert event.can_self_register(user2, now)

        event.num_online_slots = 1

        assert not event.has_free_online_slots()
        assert not event.can_self_register(user2, now)

        event.registrations[0].status = RegistrationStatus.Rejected
        assert event.has_free_online_slots()
        assert not event.can_self_register(user1, now)
        assert event.can_self_register(user2, now)

        db.session.commit()

        # Test db has been updated
        db_event = Event.query.filter_by(id=event.id).first()
        assert db_event.has_free_online_slots()
        assert not db_event.can_self_register(user1, now)
        assert db_event.can_self_register(user2, now)

class TestJsonApi(ModelTest):
    def test_autocomplete(self):

        user1 = User(mail="u1", first_name="First", last_name="User",
                     password="", license="u1", phone="")
        user2 = User(mail="u2", first_name="Second", last_name="User",
                     password="", license="u2", phone="")
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()

        users = list(find_users_by_fuzzy_name("user"))
        assert len(users) == 2
        users = list(find_users_by_fuzzy_name("rst u"))
        assert len(users) == 1
        assert users[0].mail == 'u1'
        users = list(find_users_by_fuzzy_name("sec"))
        assert len(users) == 1
        assert users[0].mail == 'u2'
        users = list(find_users_by_fuzzy_name("z"))
        assert len(users) == 0

class TestExtranetApi(flask_testing.TestCase):

    def create_app(self):

        # pass in test configuration
        app = create_app()
        return app

    def setUp(self):
        extranet.api.init()

    def test_check_license(self):
        result = extranet.api.check_license('740020189319')
        assert result.exists
        if not extranet.api.disabled():
            result = extranet.api.check_license('XXX')
            assert not result.exists


class TestExtranetApi(flask_testing.TestCase):

    VALID_LICENSE_NUMBER = environ.get('EXTRANET_TEST_LICENSE_NUMBER')

    def create_app(self):

        # pass in test configuration
        app = create_app()
        return app

    def test_check_license(self):
        result = extranet.api.check_license(self.VALID_LICENSE_NUMBER)
        assert result.exists
        expiry = result.expiry_date()
        assert expiry is None or expiry >= current_time().date()
        if not extranet.api.disabled():
            result = extranet.api.check_license('XXX')
            assert not result.exists

    def test_fetch_user_data(self):
        result = extranet.api.fetch_user_info(self.VALID_LICENSE_NUMBER)
        assert result.is_valid

    def test_license_expiry(self):
        info = extranet.LicenseInfo()
        info.renewal_date = datetime.date(2018, 10, 1)
        assert info.expiry_date() == datetime.date(2019, 10, 1)
        info.renewal_date = datetime.date(2019, 2, 2)
        assert info.expiry_date() == datetime.date(2019, 10, 1)
        info.renewal_date = datetime.date(2019, 9, 1)
        assert info.expiry_date() == datetime.date(2020, 10, 1)

class TestImportCSV(ModelTest, flask_testing.TestCase):

    csv = {
        "initiateur": "u1",
        "seats": "8",
        "internetSeats": "4",
        "registrationStart": "13/06/19 19:00",
        "registrationEnd": "14/06/19 12:00",
        "dateStart": "14/06/19 18:30",
        "dateEnd": "14/06/19 19:30",
        "categories": "",
        "title": "TITRE",
        "location": "",
        "carte": "",
        "altitude": "",
        "denivele": "",
        "cotation": "",
        "distance": "",
        "observations": "observations"
    }

    def create_app(self):

        # pass in test configuration
        app = create_app()
        return app

    def test_csv_import(self):

        user1 = User(mail="u1", first_name="First", last_name="User",
                     password="", license="u1", phone="")
        db.session.add(user1)
        db.session.commit()

        event = Event()
        fill_from_csv(event, self.csv)
        assert event.title == "TITRE"
        assert event.num_slots == 8
        assert event.num_online_slots == 4
        assert event.rendered_description == "observations"
        assert event.leaders[0].first_name == "First"


if __name__ == '__main__':
    unittest.main()
