"""
Module to calculate statistics of the event database. 

"""

from functools import lru_cache
from io import BytesIO
from math import floor
from datetime import datetime, timedelta

from sqlalchemy import func, distinct
from openpyxl import Workbook
from openpyxl.styles import Font

from collectives.models import db, Registration, Event, EventType
from collectives.models import RegistrationStatus, EventStatus, ActivityType
from collectives.models import User, EventTag
from collectives.utils.openpyxl import columns_best_fit

# Pylint does not understand that func.count IS callable.
# See https://github.com/pylint-dev/pylint/issues/1682
# pylint: disable=not-callable


class StatisticsEngine:
    """Configurable class which will output statistics"""

    CACHE_TTL = 600
    """ Number of second to cache the answers """

    creation_time = None
    """ Time when the engine is created.
    
    It is used to compare StatisticsEngine object and limit cache time"""

    activity_id = None
    """ All statistics of the engine will be limited to the activity with this id
    
    :type: int
    """

    start = None
    """ All statistics of the engine will be limited to events starting ofter this date
    
    :type: :py:class:`datetime.datetime`
    """
    end = None
    """ All statistics of the engine will be limited to events ending ofter this date
    
    :type: :py:class:`datetime.datetime`
    """

    INDEX = {
        "nb_registrations": {
            "name": "Inscriptions",
            "description": "Nombre total d'inscriptions unitaires. Une personne peut générer "
            "plusieurs inscriptions. Les coencadrants sont inclus. Les "
            "encadrants sont exclus. Les inscritions annulées, les absents, "
            "etc, sont inclus. Les événements annulés sont exclus.",
        },
        "nb_active_registrations": {
            "name": "Inscriptions réalisées",
            "description": "Nombre total d'inscriptions unitaires valides, sur des événements "
            "valides. "
            "Une personne peut générer plusieurs inscriptions. "
            "Les coencadrants sont inclus. "
            "Les encadrants sont exclus. "
            "Les inscritions anullées, les absents, etc, sont exclus. "
            "Les événements annulés sont exclus.",
        },
        "nb_registrations_by_gender": {
            "name": "Inscriptions par genre",
            "description": "Nombre total d'inscriptions unitaires groupées par genre. Une personne "
            "peut générer plusieurs inscriptions. "
            "Les coencadrants sont inclus. "
            "Les encadrants sont exclus. "
            "Les inscritions annulées, les absents, etc, sont exclus. "
            "Les événements annulés sont exclus.",
        },
        "mean_registrations_per_event": {
            "name": "Moyenne d'inscriptions par événement",
            "description": "Nombre moyen d'inscriptions unitaires par événement. "
            "Les coencadrants sont inclus. "
            "Les encadrants sont exclus. "
            "Les inscritions annulées, les absents, etc, sont exlues. "
            "Les événements annulés sont exclus.",
        },
        "mean_registrations_per_day": {
            "name": "Moyenne d'inscriptions par jour",
            "description": "Nombre moyen d'inscriptions unitaires par jour sur la période. "
            "Les coencadrants sont inclus. "
            "Les encadrants sont exclus. "
            "Les inscriptions annulées, les absents, etc, sont exclues. "
            "Les événements annulés sont exclus.",
        },
        "nb_events": {
            "name": "Nombre d'événements",
            "description": "Nombre total d'événements confirmés. "
            "Les événements annulés sont exclus.",
        },
        "nb_collectives": {
            "name": "Nombre de collectives",
            "description": 'Nombre total d\'événements de type "Collective".'
            "Les événements annulés sont exclus.",
        },
        "mean_events_per_day": {
            "name": "Moyenne d'événement par jour",
            "description": "Nombre moyen d'événement par jour sur la période. "
            "Les événements annulés sont exclus. ",
        },
        "mean_collectives_per_day": {
            "name": "Moyenne de collective par jour",
            "description": 'Nombre moyen d\'événement de type "Collective" '
            "par jour sur la période. "
            "Les événements annulés sont exclus. ",
        },
        "nb_events_by_activity_type": {
            "name": "Evènements par activité",
            "description": "Nombre d'événements confirmés, groupés par type d'activité. "
            "Les événements annulés sont exclus."
            "La somme peut être supérieure au nombre total d'événements "
            "car un événement avec deux activités compte pour chaque "
            "type d'activité.",
        },
        "nb_collectives_by_activity_type": {
            "name": "Collectives par activité",
            "description": 'Nombre d\'événements confirmés, de type "Collective" '
            "groupés par type d'activité. "
            "Les événements annulés sont exclus."
            "La somme peut être supérieure au nombre total d'événements "
            "car un événement avec deux activités compte pour chaque "
            "type d'activité.",
        },
        "nb_user_per_activity_type": {
            "name": "Participants par activité",
            "description": "Nombre d'utilisateur ayant fait au moins un événement de l'activité. "
            "Les événements annulés sont exclus."
            "La somme peut être supérieure au nombre total d'utilisateur "
            "car un utilisateur peut compter pour plusieurs types d'activité.",
        },
        "nb_events_by_event_tag": {
            "name": "Nombre d'événements par label",
            "description": "Nombre d'événements confirmés, groupés par label. "
            "Les événements annulés sont exclus."
            "La somme peut être supérieure au nombre total d'événements "
            "car un événement avec deux labels compte pour chaque "
            "label.",
        },
        "nb_events_by_event_type": {
            "name": "Nombre d'événements par type d'événement",
            "description": "Nombre d'événements confirmés, groupés par type d'événement. "
            "Les événements annulés sont exclus.",
        },
        "nb_events_by_leaders": {
            "name": "Nombre d'événements par encadrants",
            "description": "Nombre d'événements confirmés, groupés par encadrant. "
            "Les événements annulés sont exclus. "
            "La somme peut être supérieure au nombre total d'événements "
            "car un événement encadré par deux personnes compte pour chaque "
            "encadrant.",
        },
        "volunteer_time": {
            "name": "Durée d'encadrements totale",
            "description": "Nombre de journée d'encadrement."
            "Les événements annulés sont exclus. "
            "Un evènement de deux heures ou moins compte pour 1/4. "
            "Un evènement de quatre heures ou moins compte pour 1/2. "
            "Un evènement de plus de quatre heures compte pour 1. "
            "Un evènement de plus d'une journée se voit arrondi au nombre de "
            "jour supérieur. "
            "Un événement avec plusieurs encadrants compte autant qu'il y a "
            "d'encadrants. ",
        },
        "volunteer_time_by_activity_type": {
            "name": "Journées d'encadrements par activité",
            "description": "Nombre de journée d'encadrement, groupé par activité. "
            "Les événements annulés sont exclus. "
            "La somme peut être supérieure au nombre total d'événements "
            "car un événement encadré par deux personnes compte pour chaque "
            "encadrant. "
            "Un evènement de deux heures ou moins compte pour 1/4. "
            "Un evènement de quatre heures ou moins compte pour 1/2. "
            "Un evènement de plus de quatre heures compte pour 1. "
            "Un evènement de plus d'une journée se voit arrondi au nombre de "
            "jour supérieur. "
            "Un événement avec plusieurs encadrants compte autant qu'il y a "
            "d'encadrants. ",
        },
        "population_registration_number": {
            "name": "Population par nombre d'inscription",
            "description": "Nombre d'inscription par nombre d'utilisateur. "
            "Indique combien de personnes ont fait 0, 1 ou 15 sorties. ",
        },
        "nb_unregistrations_inc_late_and_unjustified_absentees_per_week": {
            "name": "Nombre de désinscriptions et absences injustifiées par semaine",
            "description": "Nombre de désinscriptions incluant les tardives et "
            "absences injustifiées par semaine. Une désinscription est jugée tardive "
            "si elle est réalisée moins de 48h (paramétrable) avant le début de l'évènement "
            "et si l'évènement requiert un type d'activité (collective, formation...)."
            "En abscisse, le temps correspond au début d'un évènement.",
        },
    }
    """ List of all statistics functions with their description to be displayed.
    
    It can be accessed directly on the function. EG: `self.nb_registrations._info` """

    def __init__(self, **kwargs) -> None:
        """Engine builder. Attribute loading are done using key word argument.

        Eg: StatisticsEngine(activity_id = 1)

        :param kwargs: see :py:class:`StatisticsEngine` attributes"""
        for attr in dir(self):
            if "__" in attr:
                continue
            if callable(getattr(self, attr)):
                continue
            if attr not in kwargs:
                continue
            setattr(self, attr, kwargs[attr])

        if "year" in kwargs:
            self.start = datetime(int(kwargs["year"]), 9, 1, 0, 0, 0)
            self.end = datetime(int(kwargs["year"]) + 1, 8, 30, 23, 59)

        self.creation_time = datetime.now()

    def nb_days(self) -> int:
        """Returns number of days during the Engine interval.

        Return None if engine does not work on an interval"""
        if self.start is None or self.end is None:
            return None
        return floor((self.end - self.start).total_seconds() / 3600 / 24)

    @lru_cache()
    def valid_activity_events(self):
        """Returns valid relevent events from cache or process it.

        Their status is Confirmed. Their type requires an activity.
        """
        query = self.global_filters(Event.query, requires_activity=True)
        return query.all()

    @lru_cache()
    def events(self):
        """Returns relevent events from cache or process it."""
        return self.global_filters(Event.query).all()

    def global_filters(self, query, requires_activity=False):
        """Add a filter to the query to look only for relevant events.

        :param query: The sqlalchemy query to fix
        :returns: The filtered query
        """
        query_type = query.column_descriptions[0]["type"]

        condition = Event.status == EventStatus.Confirmed
        if self.start:
            condition = condition & (Event.start >= self.start)
        if self.end:
            condition = condition & (Event.start <= self.end)
        if self.activity_id:
            condition = condition & (
                Event.activity_types.any(ActivityType.id == self.activity_id)
            )

        if query_type == Event:
            query = query.filter(condition)
        elif query_type == Registration:
            query = query.filter(Registration.event.has(condition))
        else:
            query = query.filter(condition)

        if requires_activity:
            query.filter(Event.event_type.has(EventType.requires_activity == True))

        return query

    @lru_cache()
    def nb_registrations(self) -> int:
        """Returns the total number of registration."""
        return self.global_filters(Registration.query).count()

    @lru_cache()
    def nb_active_registrations(self) -> int:
        """Returns the total number of active registration.
        Cf :py:meth:`collectives.models.registration.RegistrationStatus.is_valid()`
        """
        query = self.global_filters(Registration.query)
        query = query.filter(Registration.status.in_(RegistrationStatus.valid_status()))
        return query.count()

    def count_events(self, filters=None) -> int:
        """Counts events regarding some filters.

        :param list filters: Additionnal sql filters that can be used"""
        query = self.global_filters(Event.query)
        if filters:
            for condition in filters:
                query = query.filter(condition)
        return query.count()

    @lru_cache()
    def nb_events(self) -> int:
        """Returns the total number of events."""
        return self.count_events()

    @lru_cache()
    def nb_collectives(self) -> int:
        """Returns the number of events of type "Collectives" """
        condition = Event.event_type.has(EventType.name == "Collective")
        return self.count_events([condition])

    def count_mean_events_per_day(self, filters=None) -> float:
        """Count the mean number of event per day regarding some filters.

        :param list filters: Additionnal sql filters that can be used"""
        if self.nb_days() is None:
            return None
        return self.count_events(filters) / self.nb_days()

    @lru_cache()
    def mean_events_per_day(self) -> float:
        """Returns the mean number of event per day."""
        return self.count_mean_events_per_day()

    @lru_cache()
    def mean_collectives_per_day(self) -> float:
        """Returns the mean number of event of type "Collectives" per day."""
        condition = Event.event_type.has(EventType.name == "Collective")
        return self.count_mean_events_per_day([condition])

    @lru_cache()
    def nb_events_by_event_type(self) -> dict:
        """Returns the total number of events of each event type."""
        query = db.session.query(Event, func.count(Event.event_type_id))
        counts = self.global_filters(query).group_by(Event.event_type_id).all()
        counts = {c[0].event_type.name: c[1] for c in counts}
        return counts

    def count_events_by_activity_type(self, filters=None) -> dict:
        """Returns  number of events of each activity typeregarding some filters.

        :param list filters: Additionnal sql filters that can be used"""
        query = db.session.query(ActivityType, func.count(Event.id)).join(
            Event, ActivityType.events
        )
        if filters:
            for condition in filters:
                query = query.filter(condition)
        counts = self.global_filters(query).group_by(ActivityType.name).all()
        counts = {c[0].name: c[1] for c in counts}
        return counts

    @lru_cache()
    def nb_events_by_activity_type(self) -> dict:
        """Returns the total number of events of each activity type."""
        return self.count_events_by_activity_type()

    @lru_cache()
    def nb_collectives_by_activity_type(self) -> dict:
        """Returns the total number of events of type "Collectives" of each activity type."""
        condition = Event.event_type.has(EventType.name == "Collective")
        return self.count_events_by_activity_type([condition])

    @lru_cache()
    def nb_events_by_event_tag(self) -> dict:
        """Returns the total number of events of each activity type."""
        query = db.session.query(EventTag, func.count(Event.id)).join(
            Event, EventTag.event
        )
        counts = self.global_filters(query).group_by(EventTag.type).all()
        return {c[0].name: c[1] for c in counts}

    @lru_cache()
    def nb_events_by_leaders(self) -> dict:
        """Returns the total number of events of each leader."""
        query = db.session.query(User, func.count(Event.id)).join(
            Event, User.led_events
        )
        counts = self.global_filters(query).group_by(User).all()
        counts = {c[0].full_name(): c[1] for c in counts}
        return counts

    @lru_cache()
    def nb_registrations_by_gender(self) -> dict:
        """Returns the total number of registration per gender."""
        query = db.session.query(Registration, func.count(Registration.id)).join(User)
        query = query.filter(Registration.status.in_(RegistrationStatus.valid_status()))
        counts = self.global_filters(query).group_by(User.gender).all()
        counts = {c[0].user.gender.display_name(): c[1] for c in counts}
        return counts

    @lru_cache()
    def volunteer_time(self) -> int:
        """Returns the total number of volunteer hours."""
        events = self.valid_activity_events()
        return sum(event.volunteer_duration() * len(event.leaders) for event in events)

    @lru_cache()
    def volunteer_time_by_activity_type(self) -> dict:
        """Returns the total number of volunteer hours of each activity type."""
        durations = {}
        for event in self.valid_activity_events():
            for activity_type in event.activity_types:
                activity_name = activity_type.name
                duration = event.volunteer_duration() * len(event.leaders)
                durations[activity_name] = durations.get(activity_name, 0) + duration
        return durations

    @lru_cache()
    def mean_registrations_per_event(self) -> float:
        """Returns the mean number of registration per events."""
        if self.nb_events() == 0:
            return 0
        return self.nb_active_registrations() / self.nb_events()

    @lru_cache()
    def mean_registrations_per_day(self) -> float:
        """Returns the mean number of registration per day."""
        if self.nb_days() is None or self.nb_days() == 0:
            return None
        return self.nb_active_registrations() / self.nb_days()

    @lru_cache()
    def population_registration_number(self) -> dict:
        """Returns the number of user for each user registration quantity.

        :returns: index are number are registration, value is number of user with that
                    many registrations
        """
        subquery = db.session.query(User, func.count(User.id).label("count"))
        subquery = subquery.join(Registration).join(Registration.event)
        subquery = self.global_filters(subquery).group_by(User.id)
        subquery = subquery.subquery()
        counts = (
            db.session.query(subquery.c.count, func.count("count"))
            .group_by("count")
            .all()
        )
        counts = {c[0]: c[1] for c in counts}
        return counts

    @lru_cache()
    def nb_user_per_activity_type(self) -> dict:
        """Returns number of individuals users for each activity."""
        counting = func.count(distinct(User.id + "-" + ActivityType.id))
        query = db.session.query(Event, Registration, User, ActivityType, counting)
        query = self.global_filters(query)
        query = query.join(Registration, Event.registrations)
        query = query.join(User, Registration.user_id == User.id)
        query = query.join(ActivityType, Event.activity_types)
        query = query.filter(Registration.status.in_(RegistrationStatus.valid_status()))
        counts = query.group_by(ActivityType.id).all()
        return {c[3].name: c[4] for c in counts}

    @lru_cache()
    def nb_unregistrations_inc_late_and_unjustified_absentees_per_week(self) -> dict:
        """
        Returns the number of unregistrations and unjustifited absentees per week,
        split by registration status.
        """
        if "sqlite" in db.engine.name:
            week_fn = func.strftime("%Y-%W", Event.start)
        else:
            week_fn = func.date_format(Event.start, "%Y-%W")

        query = (
            db.session.query(
                week_fn.label("event_week"),
                Registration.status,
                func.count(Registration.id).label("num_unregistrations"),
            )
            .join(Event, Registration.event_id == Event.id)
            .filter(
                Registration.status.in_(
                    [
                        RegistrationStatus.SelfUnregistered,
                        RegistrationStatus.LateSelfUnregistered,
                        RegistrationStatus.UnJustifiedAbsentee,
                    ]
                ),
                Event.start < func.now(),
                Event.start >= datetime.now() - timedelta(weeks=52),
            )
            .group_by("event_week", Registration.status)
        )

        results = query.all()

        unregistrations_by_week_and_status = {}

        for event_week, status, count in results:
            if event_week not in unregistrations_by_week_and_status:
                unregistrations_by_week_and_status[event_week] = {}
            status_str = status.name if hasattr(status, "name") else str(status)
            unregistrations_by_week_and_status[event_week][status_str] = count

        return unregistrations_by_week_and_status

    def export_excel(self) -> BytesIO:
        """Generate an Excel with all statistics inside.

        Name and description are defined in
        :py:attr:`collectives.utils.stats.StatisticsEngine.__index__`

        :returns: An excel file"""
        workbook = Workbook()
        main_ws = workbook.active
        main_ws.title = "Général"
        main_ws.append(["Statistique du site des collectives"])
        main_ws["A1"].font = Font(size=20, bold=True)
        main_ws.row_dimensions[1].height = 25
        main_ws.append([""])
        main_ws.append([f"Du {self.start} au {self.end}"])
        main_ws.append([""])

        # Filter all attribute of the current engine to keep only statisctics functions
        functions = list(self.INDEX.keys())
        functions = [getattr(self, fnc) for fnc in functions]

        for fnc in functions:
            if fnc.__annotations__["return"] == dict:
                worksheet = workbook.create_sheet()
                worksheet.title = self.INDEX[fnc.__name__]["name"]
                worksheet.append([worksheet.title])
                worksheet["A1"].font = Font(size=20, bold=True)
                worksheet.row_dimensions[1].height = 25
                worksheet.append([self.INDEX[fnc.__name__]["description"]])
                worksheet.append([""])
                data = fnc()
                for key, value in data.items():
                    worksheet.append([str(key), str(value)])
                columns_best_fit(worksheet, [1, 2])
            if fnc.__annotations__["return"] in [int, float]:
                main_ws.append([self.INDEX[fnc.__name__]["name"], fnc()])

        columns_best_fit(main_ws, [1, 2])

        out = BytesIO()
        workbook.save(out)
        out.seek(0)

        return out

    def time_segment(self) -> int:
        """Returns an id of the creation time regarding ttl."""
        return floor(self.creation_time.timestamp() / self.CACHE_TTL)

    def __str__(self) -> str:
        """Returns string representation of Engine"""
        return f"{self.activity_id}/{self.start}->{self.end}/{self.time_segment()}"

    def __hash__(self) -> int:
        """Return unique hash based on StatisticsEngine parameters"""
        return hash(str(self))

    def __eq__(self, other) -> bool:
        """Check if two StatisticsEngine are equivalent."""
        return (
            self.activity_id == other.activity_id
            and self.start == other.start
            and self.end == other.end
            and self.time_segment() == other.time_segment()
        )
