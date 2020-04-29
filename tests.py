import unittest
import datetime
from os import environ
from io import StringIO

import flask_testing

# pylint: disable=C0301
from collectives import create_app
from collectives.models import db, User, ActivityType, Role, RoleIds, Event
from collectives.models import Registration, RegistrationLevels, RegistrationStatus

# pylint: enable=C0301
from collectives.api import find_users_by_fuzzy_name
from collectives.context_processor import helpers_processor
from collectives.helpers import current_time
from collectives.models.user import activity_supervisors
from collectives.utils.csv import csv_to_events

from collectives.utils import extranet


def create_test_user(email="test", user_license=""):
    user = User(
        mail=email,
        first_name="Test",
        last_name="Test",
        password="",
        license=user_license,
        enabled=True,
        phone="",
    )
    db.session.add(user)
    db.session.commit()
    return user


def create_test_activity(name="Ski"):
    activity = ActivityType(name=name, short="", order=1)
    db.session.add(activity)
    db.session.commit()
    return activity


class ModelTest(flask_testing.TestCase):
    def create_app(self):

        # pass in test configuration
        app = create_app()
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///testdb.sqlite"
        app.config["TESTING"] = True
        app.config["EXTRANET_ACCOUNT_ID"] = None
        return app

    def setUp(self):

        db.create_all()

    def tearDown(self):

        db.session.remove()
        db.drop_all()


def test_create_user():
    user = create_test_user()
    assert user in db.session


def test_create_activity():
    activity = create_test_activity()
    assert activity in db.session


def make_role(user):
    return Role(user=user, role_id=int(RoleIds.Administrator))


def make_activity_role(user, activity, role_id=RoleIds.EventLeader):
    return Role(user=user, activity_id=activity.id, role_id=int(role_id))


def commit_role(role):
    db.session.add(role)
    db.session.commit()


def make_event():
    return Event(
        title="Event",
        description="",
        num_slots=2,
        num_online_slots=0,
        start=datetime.datetime.now() + datetime.timedelta(days=1),
        end=datetime.datetime.now() + datetime.timedelta(days=2),
    )


def make_registration(user):
    datetime.datetime.timestamp(datetime.datetime.now())
    return Registration(
        user=user, status=RegistrationStatus.Active, level=RegistrationLevels.Normal
    )


class TestRoles(ModelTest):
    @staticmethod
    def test_add_role():
        user = create_test_user()

        role = make_role(user)
        user.roles.append(role)

        db.session.commit()

        assert role in db.session

        retrieved_user = User.query.filter_by(id=user.id).first()
        assert len(retrieved_user.roles) == 1
        assert retrieved_user.is_admin()
        assert retrieved_user.is_moderator()
        assert not retrieved_user.can_lead_activity(0)

    @staticmethod
    def test_add_activity_role():
        user = create_test_user()
        activity1 = create_test_activity("1")
        activity2 = create_test_activity("2")

        role = make_activity_role(user, activity1)
        user.roles.append(role)
        commit_role(role)

        assert role in db.session

        retrieved_user = User.query.filter_by(id=user.id).first()
        assert len(retrieved_user.roles) == 1
        assert not retrieved_user.is_admin()
        assert not retrieved_user.is_moderator()
        assert retrieved_user.can_lead_activity(activity1.id)
        assert not retrieved_user.can_lead_activity(activity2.id)

        role = make_activity_role(user, activity2, RoleIds.ActivitySupervisor)
        user.roles.append(role)
        commit_role(role)

        supervisors = activity_supervisors([activity1])
        assert len(supervisors) == 0
        supervisors = activity_supervisors([activity2])
        assert len(supervisors) == 1
        supervisors = activity_supervisors([activity1, activity2])
        assert len(supervisors) == 1


class TestEvents(ModelTest):
    @staticmethod
    def test_add_event():
        event = make_event()
        db.session.add(event)
        db.session.commit()
        return event

    @staticmethod
    def test_event_validity():
        user1 = create_test_user("email1", "license1")
        user2 = create_test_user("email2", "license2")
        activity1 = create_test_activity("1")
        activity2 = create_test_activity("2")

        user1.roles.append(Role(role_id=RoleIds.EventLeader, activity_id=activity1.id))
        user2.roles.append(Role(role_id=RoleIds.EventLeader, activity_id=activity2.id))
        db.session.commit()

        event = make_event()
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
        event.num_online_slots = 1
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

        event.num_online_slots = 1
        event.registration_open_time = datetime.datetime.now()
        event.registration_close_time = datetime.datetime.now() + datetime.timedelta(
            days=1
        )

        assert event.is_registration_open_at_time(datetime.datetime.now())

        event.registration_open_time = (
            event.registration_close_time + datetime.timedelta(hours=1)
        )
        assert not event.opens_before_closes()
        assert not event.is_valid()

        event.registration_open_time = datetime.datetime.combine(
            event.end, datetime.datetime.min.time()
        ) + datetime.timedelta(days=1)
        event.registration_close_time = (
            event.registration_open_time + datetime.timedelta(hours=1)
        )
        assert event.opens_before_closes()
        assert not event.opens_before_ends()
        assert not event.is_valid()

        assert not event.is_registration_open_at_time(datetime.datetime.now())


class TestRegistrations(TestEvents):
    @staticmethod
    def test_add_registration():
        event = make_event()
        event.num_online_slots = 2
        event.registration_open_time = datetime.datetime.now()
        event.registration_close_time = datetime.datetime.now() + datetime.timedelta(
            days=1
        )

        db.session.add(event)
        db.session.commit()

        now = datetime.datetime.now()
        assert event.is_registration_open_at_time(now)
        assert event.has_free_online_slots()

        user1 = create_test_user("email1", "license1")
        user2 = create_test_user("email2", "license2")

        assert event.can_self_register(user1, now)
        assert event.can_self_register(user2, now)

        event.registrations.append(make_registration(user1))
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
    @staticmethod
    def test_autocomplete():

        user1 = User(
            mail="u1",
            first_name="First",
            last_name="User",
            password="",
            license="u1",
            phone="",
        )
        user2 = User(
            mail="u2",
            first_name="Second",
            last_name="User",
            password="",
            license="u2",
            phone="",
        )
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()

        users = list(find_users_by_fuzzy_name("user"))
        assert len(users) == 2
        users = list(find_users_by_fuzzy_name("rst u"))
        assert len(users) == 1
        assert users[0].mail == "u1"
        users = list(find_users_by_fuzzy_name("sec"))
        assert len(users) == 1
        assert users[0].mail == "u2"
        users = list(find_users_by_fuzzy_name("z"))
        assert len(users) == 0


class TestExtranetApi(flask_testing.TestCase):

    VALID_LICENSE_NUMBER = environ.get("EXTRANET_TEST_LICENSE_NUMBER")

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
            result = extranet.api.check_license("XXX")
            assert not result.exists

    def test_fetch_user_data(self):
        result = extranet.api.fetch_user_info(self.VALID_LICENSE_NUMBER)
        assert result.is_valid

    @staticmethod
    def test_license_expiry():
        info = extranet.LicenseInfo()
        info.renewal_date = datetime.date(2018, 10, 1)
        assert info.expiry_date() == datetime.date(2019, 10, 1)
        info.renewal_date = datetime.date(2019, 2, 2)
        assert info.expiry_date() == datetime.date(2019, 10, 1)
        info.renewal_date = datetime.date(2019, 9, 1)
        assert info.expiry_date() == datetime.date(2020, 10, 1)


class TestImportCSV(ModelTest):

    # pylint: disable=C0301
    csv = "TEST ,740020000001,mardi26,mardi 26 novembre 2019,26/11/19 7:00,mardi 26 novembre 2019,26/11/19 7:00,19/11/19 7:00,25/11/19 12:00, ,Aiguille des Calvaires,Aravis, ,2322,1200,F, , ,8,4"

    def test_csv_import(self):

        user1 = User(
            mail="u1",
            first_name="First",
            last_name="User",
            password="",
            license="740020000001",
            phone="",
        )
        db.session.add(user1)
        db.session.commit()

        event = Event()

        output = StringIO(self.csv)

        events, processed, failed = csv_to_events(
            output, "{altitude}m-{denivele}m-{cotation}"
        )
        event = events[0]
        assert processed == 1
        assert failed == []
        assert event.title == "Aiguille des Calvaires"
        assert event.num_slots == 8
        assert event.num_online_slots == 4
        assert "2322m-1200m-F" in event.rendered_description
        assert event.leaders[0].first_name == "First"


class TestFormatDate(ModelTest):
    @staticmethod
    def test_format_date():
        # Null date
        date_test = None
        date_format = helpers_processor()["format_date"](date_test)
        assert date_format == "N/A"

        # le 26 avril à 18h -> le 26 avril
        date_test = datetime.datetime(2020, 4, 26, 18, 0, 0)
        date_format = helpers_processor()["format_date"](date_test)
        assert date_format == "dimanche 26 avril 2020"

    @staticmethod
    def test_format_time():
        # Null date
        date_test = None
        date_format = helpers_processor()["format_time"](date_test)
        assert date_format == "N/A"

        # le 26 avril à 18h -> 18h00
        date_test = datetime.datetime(2020, 4, 26, 18, 0, 0)
        date_format = helpers_processor()["format_time"](date_test)
        assert date_format == "18h00"

    @staticmethod
    def test_format_datetime_range():
        # le 26 avril
        start = datetime.datetime(2020, 4, 26, 0, 0, 0)
        end = datetime.datetime(2020, 4, 26, 0, 0, 0)
        date_format = helpers_processor()["format_datetime_range"](start, end)
        assert date_format == "dimanche 26 avril 2020"

        # le 26 avril à 18h
        start = datetime.datetime(2020, 4, 26, 18, 0, 0)
        end = datetime.datetime(2020, 4, 26, 18, 0, 0)
        date_format = helpers_processor()["format_datetime_range"](start, end)
        assert date_format == "dimanche 26 avril 2020 à 18h00"

        # le 26 avril de 8h à 18h30
        start = datetime.datetime(2020, 4, 26, 8, 0, 0)
        end = datetime.datetime(2020, 4, 26, 18, 30, 0)
        date_format = helpers_processor()["format_datetime_range"](start, end)
        assert date_format == "dimanche 26 avril 2020 de 8h00 à 18h30"

        # du 26 avril au 27 avril
        start = datetime.datetime(2020, 4, 26, 0, 0, 0)
        end = datetime.datetime(2020, 4, 27, 0, 0, 0)
        date_format = helpers_processor()["format_datetime_range"](start, end)
        assert date_format == "du dimanche 26 avril 2020 au lundi 27 avril 2020"

        # du 26 avril à 8h au 27 avril à 18h30
        start = datetime.datetime(2020, 4, 26, 8, 0, 0)
        end = datetime.datetime(2020, 4, 27, 18, 30, 0)
        date_format = helpers_processor()["format_datetime_range"](start, end)
        assert (
            date_format
            == "du dimanche 26 avril 2020 à 8h00 au lundi 27 avril 2020 à 18h30"
        )

    @staticmethod
    def test_format_date_range():
        # le 26 avril de 8h à 18h -> le 26 avril
        start = datetime.datetime(2020, 4, 26, 8, 0, 0)
        end = datetime.datetime(2020, 4, 26, 18, 0, 0)
        date_format = helpers_processor()["format_date_range"](start, end)
        assert date_format == "dim. 26 avr."

        # du 26 avril à 8h au 27 avril à 18h30 -> du 26 avril au 27 avril
        start = datetime.datetime(2020, 4, 26, 8, 0, 0)
        end = datetime.datetime(2020, 4, 27, 18, 30, 0)
        date_format = helpers_processor()["format_date_range"](start, end)
        assert date_format == "du dim. 26 avr. au lun. 27 avr."


if __name__ == "__main__":
    unittest.main()
