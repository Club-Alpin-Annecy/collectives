"""Module computing per-leader statistics for the yearly leader review.

The review helps an activity supervisor check, typically at the start of a season,
which declared leaders of an activity still lead events, and which ones may need
their role removed.

Seasons follow the FFCAM year: from the 1st of September to the 31st of August.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Tuple

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from collectives.models import (
    ActivityType,
    Event,
    EventStatus,
    Registration,
    RegistrationLevels,
    RegistrationStatus,
    Role,
    RoleIds,
    User,
    db,
)
from collectives.utils.time import current_time, get_ffcam_year

# Pylint does not understand that func.max IS callable.
# pylint: disable=not-callable

INACTIVITY_SEASONS = 2
""" Number of full past seasons without any led event after which a leader is
considered inactive.

:type: int
"""


def season_start(year: int) -> datetime:
    """:return: the start of the season beginning in ``year``"""
    return datetime(year, 9, 1)


@dataclass
class LeaderReview:
    """Statistics of a leader role holder for an activity."""

    role: Role
    """ The reviewed role """

    events_per_season: Dict[int, int] = field(default_factory=dict)
    """ Number of led or co-led events, per season start year """

    last_event_start: datetime | None = None
    """ Start of the most recent past led or co-led event, if any """

    nb_upcoming_events: int = 0
    """ Number of led or co-led events which have not started yet """

    is_new: bool = False
    """ Whether the role has been granted recently, during the previous or current
    season """

    is_inactive: bool = False
    """ Whether the leader has not led any event for :py:data:`INACTIVITY_SEASONS`
    full seasons """

    @property
    def user(self) -> User:
        """:return: the user holding the reviewed role"""
        return self.role.user

    @property
    def can_be_removed(self) -> bool:
        """:return: whether an activity supervisor may remove the role"""
        return self.role.role_id in RoleIds.all_supervisor_manageable()

    @property
    def needs_attention(self) -> bool:
        """:return: whether the role should be checked by the supervisor"""
        return self.is_inactive or not self.user.is_active


class LeadersReview:
    """Per-leader statistics of an activity, for the current season review."""

    def __init__(self, activity: ActivityType, now: datetime | None = None):
        """
        :param activity: The reviewed activity
        :param now: Reference time, defaults to current time
        """
        self.activity = activity
        self.now = now or current_time()

        self.current_season = get_ffcam_year(self.now.date())
        """ Start year of the current season """

        self.seasons = [
            self.current_season - i for i in range(INACTIVITY_SEASONS, -1, -1)
        ]
        """ Start years of the displayed seasons, oldest first, current one last """

        self.leaders = self._compute()
        """ Reviewed leaders, those needing attention first """

    def _roles(self) -> List[Role]:
        """:return: the activity-related roles of the reviewed activity"""
        query = Role.query.filter(Role.activity_id == self.activity.id)
        query = query.filter(Role.role_id.in_(RoleIds.all_relates_to_activity()))
        # Roles are expected to have a user, and the review accesses it for
        # every row: load it now rather than one query per role holder.
        query = query.filter(Role.user_id.isnot(None))
        return query.options(joinedload(Role.user)).all()

    def _activity_events_filter(self):
        """:return: SQL condition on confirmed events of the reviewed activity"""
        return (Event.status == EventStatus.Confirmed) & Event.activity_types.any(
            ActivityType.id == self.activity.id
        )

    def _led_query(self, *columns):
        """:return: query on events led by users, with requested columns"""
        query = db.session.query(User.id, *columns).join(Event, User.led_events)
        return query.filter(self._activity_events_filter())

    def _coled_query(self, *columns):
        """:return: query on events co-led by users, with requested columns"""
        query = db.session.query(Registration.user_id, *columns).join(
            Registration.event
        )
        query = query.filter(Registration.level == RegistrationLevels.CoLeader)
        query = query.filter(Registration.status.in_(RegistrationStatus.valid_status()))
        return query.filter(self._activity_events_filter())

    def _recent_events(self, user_ids: List[int]) -> Set[Tuple[int, int, datetime]]:
        """:return: (user id, event id, event start) of all led or co-led events
        within displayed seasons. Each event is counted once per user."""
        since = season_start(self.seasons[0])
        rows = set()
        for query in (
            self._led_query(Event.id, Event.start).filter(User.id.in_(user_ids)),
            self._coled_query(Event.id, Event.start).filter(
                Registration.user_id.in_(user_ids)
            ),
        ):
            rows.update(tuple(row) for row in query.filter(Event.start >= since))
        return rows

    def _last_past_events(self, user_ids: List[int]) -> Dict[int, datetime]:
        """:return: start of the most recent past led or co-led event, per user"""
        last = {}
        for query in (
            self._led_query(func.max(Event.start))
            .filter(User.id.in_(user_ids))
            .group_by(User.id),
            self._coled_query(func.max(Event.start))
            .filter(Registration.user_id.in_(user_ids))
            .group_by(Registration.user_id),
        ):
            for user_id, start in query.filter(Event.start < self.now):
                if user_id not in last or start > last[user_id]:
                    last[user_id] = start
        return last

    def _compute(self) -> List[LeaderReview]:
        """:return: the review of each activity role"""
        roles = self._roles()
        if not roles:
            return []
        user_ids = list({role.user_id for role in roles})

        events_per_season = {
            user_id: dict.fromkeys(self.seasons, 0) for user_id in user_ids
        }
        nb_upcoming_events = dict.fromkeys(user_ids, 0)
        for user_id, _, start in self._recent_events(user_ids):
            if start >= self.now:
                nb_upcoming_events[user_id] += 1
            season = get_ffcam_year(start.date())
            if season in events_per_season[user_id]:
                events_per_season[user_id][season] += 1
        last_past_events = self._last_past_events(user_ids)

        reviews = [
            LeaderReview(
                role=role,
                events_per_season=events_per_season[role.user_id],
                last_event_start=last_past_events.get(role.user_id),
                nb_upcoming_events=nb_upcoming_events[role.user_id],
            )
            for role in roles
        ]

        new_since = season_start(self.current_season - 1)
        inactive_before = season_start(self.current_season - INACTIVITY_SEASONS)
        for review in reviews:
            creation_time = review.role.creation_time
            review.is_new = creation_time is not None and creation_time >= new_since
            review.is_inactive = (
                not review.is_new
                and review.nb_upcoming_events == 0
                and (
                    review.last_event_start is None
                    or review.last_event_start < inactive_before
                )
            )

        return sorted(
            reviews,
            key=lambda r: (
                not r.needs_attention,
                r.last_event_start or datetime.min,
                r.user.last_name,
                r.user.first_name,
            ),
        )

    def season_label(self, season: int) -> str:
        """:return: display label of a season, eg "2025/26" """
        return f"{season}/{(season + 1) % 100:02d}"
