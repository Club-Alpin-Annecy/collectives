"""Module to creaate a fixture db barely rich enough to test statistics engine"""

import pytest

from collectives.models import (
    ActivityType,
    EventTag,
    EventType,
    Registration,
    RegistrationLevels,
    RegistrationStatus,
    db,
)

# pylint: disable=unused-argument,too-many-arguments
# pylint: disable=too-many-positional-arguments


@pytest.fixture
def stats_env(
    event1_with_reg,
    user1,
    user3,
    event2,
    past_event,
    tagged_event,
    cancelled_event,
    draft_event,
    paying_event,
    event3,
    leader2_user_with_event,
    minor_user,
):
    """Fixture with several event to test statistics engine."""
    canyon = ActivityType.query.filter_by(name="Canyon").first()
    escalade = ActivityType.query.filter_by(name="Escalade").first()
    event2.activity_types = [canyon]
    event2.registrations.append(
        Registration(
            user_id=user1.id,
            status=RegistrationStatus.Active,
            level=RegistrationLevels.Normal,
            is_self=True,
        ),
    )
    event2.registrations.append(
        Registration(
            user_id=minor_user.id,
            status=RegistrationStatus.Active,
            level=RegistrationLevels.Normal,
            is_self=True,
        )
    )
    event2.tag_refs.append(EventTag(6))

    party = EventType.query.filter_by(name="Soirée").first()
    event3.tag_refs.append(EventTag(10))
    event3.tag_refs.append(EventTag(11))
    event3.activity_types = [canyon, escalade]
    event3.event_type = party

    past_event.tag_refs.append(EventTag(6))
    past_event.registrations.append(
        Registration(
            user_id=user1.id,
            status=RegistrationStatus.Active,
            level=RegistrationLevels.Normal,
            is_self=True,
        )
    )
    past_event.registrations.append(
        Registration(
            user_id=user3.id,
            status=RegistrationStatus.Active,
            level=RegistrationLevels.Normal,
            is_self=True,
        )
    )

    db.session.add_all([event2, event3, past_event])
    db.session.commit()
