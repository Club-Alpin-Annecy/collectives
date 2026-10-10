"""Module to help export informations."""

import csv
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO, TextIOWrapper
from typing import List, Optional, Tuple

from openpyxl import Workbook
from sqlalchemy.orm import joinedload, selectinload

from collectives.models import (
    ActivityType,
    Event,
)
from collectives.models.badge import Badge
from collectives.models.registration import Registration
from collectives.models.utils import ChoiceEnum
from collectives.utils.misc import deepgetattr
from collectives.utils.time import current_time


def export_roles(roles):
    """Create an excel with the input role and related user.

    :param roles:
    :type roles: array of :py:class:`collectives.models.role.Role`
    :returns: The excel with all info
    :rtype: :py:class:`io.BytesIO`
    """
    workbook = Workbook()
    worksheet = workbook.active
    fields = {
        "user.license": "Licence",
        "user.first_name": "Prénom",
        "user.last_name": "Nom",
        "user.mail": "Email",
        "user.phone": "Téléphone",
        "activity_type.name": "Activité",
        "name": "Role",
    }
    worksheet.append(list(fields.values()))

    for role in roles:
        worksheet.append([deepgetattr(role, field, "-") for field in fields])

    # set column width
    for i in range(ord("A"), ord("A") + len(fields)):
        worksheet.column_dimensions[chr(i)].width = 25

    out = BytesIO()
    workbook.save(out)
    out.seek(0)

    return out


def export_badges(badges: list[Badge]) -> BytesIO:
    """Create an excel with the input badge and related user.

    :param badges: List of badges to export
    :returns: The excel with all info
    """
    workbook = Workbook()
    worksheet = workbook.active
    fields = {
        "user.license": "Licence",
        "user.first_name": "Prénom",
        "user.last_name": "Nom",
        "user.mail": "Email",
        "user.phone": "Téléphone",
        "activity_type.name": "Activité",
        "name": "Badge",
        "level_name": "Niveau",
        "expiration_date": "Date Expiration",
    }
    worksheet.append(list(fields.values()))

    for badge in badges:
        worksheet.append(
            [deepgetattr(badge, field, "-", resolve_method=True) for field in fields]
        )

    # set column width
    for i in range(ord("A"), ord("A") + len(fields)):
        worksheet.column_dimensions[chr(i)].width = 25

    out = BytesIO()
    workbook.save(out)
    out.seek(0)

    return out


def export_users(users):
    """Create an excel with the input users.

    :param users: List of users to export
    :type users: list of :py:class:`collectives.models.user.User`
    :returns: The excel with all info
    :rtype: :py:class:`io.BytesIO`
    """
    workbook = Workbook()
    worksheet = workbook.active
    fields = {
        "license": "Licence",
        "first_name": "Prénom",
        "last_name": "Nom",
        "mail": "Email",
        "phone": "Téléphone",
    }
    worksheet.append(list(fields.values()))

    for user in users:
        worksheet.append([deepgetattr(user, field, "-") for field in fields])

    for i in range(ord("A"), ord("A") + len(fields)):
        worksheet.column_dimensions[chr(i)].width = 25

    out = BytesIO()
    workbook.save(out)
    out.seek(0)

    return out


def export_retex(events):
    """Create an Excel document listing retex (and missing retex) for a set of events.

    :param events: List of events to export
    :type events: list of :py:class:`collectives.models.event.Event`
    :returns: The excel with all info
    :rtype: :py:class:`io.BytesIO`
    """
    workbook = Workbook()
    worksheet = workbook.active
    fields = [
        "Date",
        "Titre",
        "Activité(s)",
        "Encadrant principal",
        "Statut",
        "Description",
    ]
    worksheet.append(fields)

    for event in events:
        retex = event.retex
        worksheet.append(
            [
                event.start.strftime("%d/%m/%Y"),
                event.title,
                event.activity_type_names,
                event.main_leader.full_name() if event.main_leader else "-",
                retex.status.display_name() if retex else "Retex Absent",
                retex.description if retex else "",
            ]
        )

    # set column width
    for i in range(ord("A"), ord("A") + len(fields)):
        worksheet.column_dimensions[chr(i)].width = 25

    out = BytesIO()
    workbook.save(out)
    out.seek(0)

    return out


def export_users_registered(event):
    """Create an Excel document with the contact information of registered users at an event.

    :param event:
    :type event: :py:class:`collectives.models.event.event`
    :returns: The excel with all info
    :rtype: :py:class:`io.BytesIO`
    """
    workbook = Workbook()
    worksheet = workbook.active
    fields = [
        "Licence",
        "Prénom",
        "Nom",
        "Téléphone",
        "Email",
        "En cas d'accident",
    ]
    worksheet.append(fields)

    for reg in event.active_registrations():
        temp = [
            reg.user.license,
            reg.user.first_name,
            reg.user.last_name.upper(),
            reg.user.phone,
            reg.user.mail,
            f"{reg.user.emergency_contact_name} ({reg.user.emergency_contact_phone})",
        ]
        worksheet.append(temp)

    # set column width
    for i in range(ord("A"), ord("A") + len(fields)):
        worksheet.column_dimensions[chr(i)].width = 25

    out = BytesIO()
    workbook.save(out)
    out.seek(0)

    return out


def _csv_value(value):
    """Converts a database value to a csv-friendly string.

    :param value: The value to convert
    :return: The converted value
    """
    if value is None:
        return ""
    if isinstance(value, ChoiceEnum):
        return value.name
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return value


DBEXPORT_REGISTRATION_COLUMNS: Tuple[str, ...] = (
    "ID inscription",
    "ID événement",
    "Etat inscription",
    "registration_level",
    "Auto-inscription",
    "Date d'inscription",
    "ID participant",
    "Participant",
    "Category de license",
    "Type d'utilisateur",
    "Genre",
    "Titre",
    "Date de RDV",
    "Date de fin",
    "Nombre de participants",
    "Nombre de participants internet",
    "Nombre de places en liste d'attente",
    "Nombre de participants incluent les encadrants",
    "Ouverture des inscriptions",
    "Fermeture des inscriptions",
    "Etat événement",
    "Visibilité événement",
    "ID Encadrant principal",
    "Type d'événement",
    "Activité",
)

DBEXPORT_LEADER_COLUMNS: Tuple[str, ...] = (
    "ID événement",
    "ID encadrant",
    "Encadrant",
    "Catégorie de license",
    "Type d'utilisateur",
    "Genre",
    "Titre",
    "Date de RDV",
    "Date de fin",
    "Nombre de participants",
    "Nombre de participants internet",
    "Nombre de places en liste d'attente",
    "Nombre de participants incluent les encadrants",
    "Ouverture des inscriptions",
    "Fermeture des inscriptions",
    "Etat événement",
    "Visibilité événement",
    "ID Encadrant principal",
    "Type d'événement",
    "Activité",
)

DBEXPORT_REGISTRATIONS_CSV: str = "inscriptions.csv"
DBEXPORT_LEADERS_CSV: str = "encadrants.csv"


def _user_fields(user) -> List:
    """Builds the fixed user columns shared by the two csv files.

    :param user: The user, or None if the registration has no user.
    :return: The list of field values.
    """
    if user is None:
        return [None, "", None, None, None]
    return [
        user.id,
        f"{user.first_name} {user.last_name}",
        user.license_category,
        user.type,
        user.gender,
    ]


@dataclass
class DatabaseExport:
    """Result of a raw database export.

    The zip is built entirely in memory, so there is nothing to clean up.
    """

    stream: BytesIO
    """Seekable stream holding the zip file containing the csv files."""

    download_name: str
    """Name to advertise for the downloaded zip file."""

    row_counts: dict
    """Number of rows written per csv file."""


class DatabaseExportService:
    """Builds a raw database export as a zip of csv files.

    The csv columns are fixed (see :data:`DBEXPORT_REGISTRATION_COLUMNS` and
    :data:`LEADER_COLUMNS`), so only an approved set of personal data is
    exported (see ``tests/test_database_export.py``). The activity supervision
    filters (year, activity) restrict the exported events. Contrary to the
    statistics engine, every event status is included.
    """

    def __init__(
        self,
        year: Optional[int] = None,
        activity_id: Optional[int] = None,
    ) -> None:
        """Creates a new export service.

        :param year: FFCAM year to restrict events to. None means no date restriction.
        :param activity_id: Activity to restrict to. None means all.
        """
        self.year = year
        self.activity_id = activity_id

        self.start = None
        self.end = None
        if year is not None:
            self.start = datetime(int(year), 9, 1, 0, 0, 0)
            self.end = datetime(int(year) + 1, 8, 30, 23, 59)

    def _event_conditions(self) -> List:
        """Builds the conditions restricting the exported events.

        :return: The list of SQLAlchemy conditions.
        """
        conditions = []
        if self.start is not None:
            conditions.append(Event.start >= self.start)
        if self.end is not None:
            conditions.append(Event.start <= self.end)
        if self.activity_id:
            conditions.append(
                Event.activity_types.any(ActivityType.id == self.activity_id)
            )
        return conditions

    def _events_query(self):
        """Builds the events query restricted by the export filters.

        The relationships needed to build the csv rows are eager loaded to
        avoid N+1 queries.

        :return: The query of matching events.
        """
        return (
            Event.query.filter(*self._event_conditions())
            .order_by(Event.id)
            .options(
                selectinload(Event.registrations).joinedload(Registration.user),
                selectinload(Event.leaders),
            )
        )

    @staticmethod
    def _event_fields(event) -> List:
        """Builds the fixed event columns shared by the two csv files.

        :param event: The event to describe.
        :return: The list of field values.
        """
        return [
            event.title,
            event.start,
            event.end,
            event.num_slots,
            event.num_online_slots,
            event.num_waiting_list,
            event.include_leaders_in_counts,
            event.registration_open_time,
            event.registration_close_time,
            event.status,
            event.visibility,
            event.main_leader_id,
        ]

    def _registration_rows(self, events) -> List:
        """Builds the rows of the registrations csv file.

        Each registration yields one row per activity type of its event, so
        that the csv keeps one row per (registration, activity) couple.

        :param events: The events to export.
        :return: The list of rows (column order follows
            :data:`DBEXPORT_REGISTRATION_COLUMNS`).
        """
        rows = []
        for event in events:
            event_fields = self._event_fields(event)
            for registration in event.registrations:
                for activity_type in event.activity_types or [None]:
                    rows.append(
                        [
                            registration.id,
                            registration.event_id,
                            registration.status,
                            registration.level,
                            registration.is_self,
                            registration.registration_time,
                            *_user_fields(registration.user),
                            *event_fields,
                            event.event_type.name if event.event_type else None,
                            activity_type.name if activity_type else None,
                        ]
                    )
        return rows

    def _leader_rows(self, events) -> List:
        """Builds the rows of the leaders csv file.

        Each leader yields one row per activity type of its event, so that the
        csv keeps one row per (leader, activity) couple.

        :param events: The events to export.
        :return: The list of rows (column order follows :data:`LEADER_COLUMNS`).
        """
        rows = []
        for event in events:
            event_fields = self._event_fields(event)
            for leader in event.leaders:
                for activity_type in event.activity_types or [None]:
                    rows.append(
                        [
                            event.id,
                            *_user_fields(leader),
                            *event_fields,
                            event.event_type.name if event.event_type else None,
                            activity_type.name if activity_type else None,
                        ]
                    )
        return rows

    @staticmethod
    def _write_csv(binary_file, headers, rows) -> int:
        """Writes an iterable of rows as csv into a zip entry.

        :param binary_file: The writable binary stream (a zip entry).
        :param headers: The column names.
        :param rows: An iterable of row value lists.
        :return: The number of written rows.
        """
        count = 0
        with TextIOWrapper(binary_file, encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.writer(csv_file, delimiter=";")
            writer.writerow(headers)
            for row in rows:
                writer.writerow([_csv_value(value) for value in row])
                count += 1
        return count

    def export(self) -> DatabaseExport:
        """Builds the csv files and bundles them into an in-memory zip file.

        :return: The export result.
        """
        year = self.year if self.year is not None else "all"
        timestamp = current_time().strftime("%Y%m%d-%H%M%S")
        download_name = f"export_{year}_{timestamp}.zip"

        events = list(self._events_query())
        row_counts = {}
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            files = (
                (
                    DBEXPORT_REGISTRATIONS_CSV,
                    DBEXPORT_REGISTRATION_COLUMNS,
                    self._registration_rows(events),
                ),
                (
                    DBEXPORT_LEADERS_CSV,
                    DBEXPORT_LEADER_COLUMNS,
                    self._leader_rows(events),
                ),
            )
            for filename, headers, rows in files:
                with archive.open(filename, "w") as entry:
                    row_counts[filename] = self._write_csv(entry, headers, rows)
        buffer.seek(0)

        return DatabaseExport(buffer, download_name, row_counts)
