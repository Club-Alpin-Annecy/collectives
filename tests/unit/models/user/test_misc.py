"""Test :py:mod:`collectives.models.user.misc`"""

import datetime

from collectives.models import RegistrationStatus

# pylint: disable=unused-argument,too-many-arguments


def test_attendance_report(
    app, user1, event1_with_reg, event2_with_reg, user5, user3, shopping_event_with_reg
):
    """Test :py:meth:`collectives.models.user.misc.UserMiscMixin.attendance_report`"""

    event1_with_reg.start = datetime.datetime.now() - datetime.timedelta(days=3)

    report = user1.attendance_report()
    assert report[RegistrationStatus.Active] == 2

    report = user3.attendance_report()
    assert report[RegistrationStatus.SelfUnregistered] == 1
    assert report[RegistrationStatus.Active] == 1

    report = user5.attendance_report()
    assert len(report) == 0

    report = user1.attendance_report(datetime.timedelta(days=1))
    assert len(report) == 1


def test_attendance_grade(
    app, user1, event1_with_reg, event2_with_reg, user5, user3, shopping_event_with_reg
):
    """Test :py:meth:`collectives.models.user.misc.UserMiscMixin.attendance_grade`"""

    event1_with_reg.start = datetime.datetime.now() - datetime.timedelta(days=3)
    event2_with_reg.start = datetime.datetime.now() - datetime.timedelta(days=3)

    assert user1.attendance_grade() == "A"
    assert user3.attendance_grade() == "C"
    assert user3.attendance_grade(datetime.timedelta(days=2)) == "A"
    assert user5.attendance_grade() == "A"
