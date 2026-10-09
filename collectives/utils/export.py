"""Module to help export informations."""

import csv
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from typing import List, Optional

from openpyxl import Workbook
from sqlalchemy import select

from collectives.models import (
    ActivityType,
    Configuration,
    Event,
    EventType,
    Registration,
    User,
    db,
)
from collectives.models.badge import Badge
from collectives.models.event.model import event_activity_types, event_leaders
from collectives.models.utils import ChoiceEnum
from collectives.utils.misc import deepgetattr
from collectives.utils.time import current_time


def _club_file_identifier() -> str:
    """Returns a filename-safe identifier for the club.

    Prefers the codified club identifier (`CLUB_PREFIX`). Otherwise falls back
    to the club name with every non-alphanumeric character removed, so that
    spaces and special characters do not end up in the file name.

    :return: The club identifier to use in file names.
    """
    prefix = (Configuration.CLUB_PREFIX or "").strip()
    identifier = prefix or Configuration.CLUB_NAME
    identifier = "".join(char for char in identifier if char.isalnum())
    return identifier or "club"


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


@dataclass
class DatabaseExport:
    """Result of a raw database export.

    The files live in a temporary directory that must be removed once the
    response has been sent, see :py:meth:`DatabaseExport.cleanup`.
    """

    path: str
    """Path to the zip file containing the csv files."""

    download_name: str
    """Name to advertise for the downloaded zip file."""

    tmpdir: str
    """Temporary directory holding the zip and csv files."""

    row_counts: dict
    """Number of rows written per csv file."""

    def cleanup(self) -> None:
        """Removes the temporary directory. Safe to call several times."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class DatabaseExportService:
    """Builds a raw database export as a zip of csv files.

    The queries are fixed and select only an approved set of columns (see
    ``tests/test_database_export.py``). The stats filters (year, event types,
    activity) are appended to each query. Contrary to the statistics engine,
    every event status is included.
    """

    def __init__(
        self,
        year: Optional[int] = None,
        event_type_ids: Optional[List[int]] = None,
        activity_id: Optional[int] = None,
    ) -> None:
        """Creates a new export service.

        :param year: FFCAM year to restrict events to. None means no date restriction.
        :param event_type_ids: Event types to restrict to. Empty means all.
        :param activity_id: Activity to restrict to. None means all.
        """
        self.year = year
        self.event_type_ids = list(event_type_ids) if event_type_ids else None
        self.activity_id = activity_id

        self.start = None
        self.end = None
        if year is not None:
            self.start = datetime(int(year), 9, 1, 0, 0, 0)
            self.end = datetime(int(year) + 1, 8, 30, 23, 59)

    def _event_conditions(self) -> List:
        """Builds the SQL conditions applied to the joined events.

        :return: The list of SQLAlchemy conditions.
        """
        conditions = []
        if self.start is not None:
            conditions.append(Event.start >= self.start)
        if self.end is not None:
            conditions.append(Event.start <= self.end)
        if self.event_type_ids:
            conditions.append(Event.event_type_id.in_(self.event_type_ids))
        if self.activity_id:
            conditions.append(
                Event.activity_types.any(ActivityType.id == self.activity_id)
            )
        return conditions

    def registration_query(self):
        """Builds the registrations export query.

        :return: The SQLAlchemy select statement.
        """
        return (
            select(
                Registration.id.label("registration_id"),
                Registration.event_id,
                Registration.status.label("registration_status"),
                Registration.level.label("registration_level"),
                Registration.is_self.label("registration_is_self"),
                Registration.registration_time,
                User.id.label("user_id"),
                (User.first_name + " " + User.last_name).label("user_name"),
                User.license_category,
                User.type.label("user_type"),
                User.gender,
                Event.title.label("event_title"),
                Event.start.label("event_start"),
                Event.end.label("event_end"),
                Event.num_slots.label("event_num_slots"),
                Event.num_online_slots.label("event_num_online_slots"),
                Event.num_waiting_list.label("event_num_waiting_list"),
                Event.include_leaders_in_counts.label(
                    "event_include_leaders_in_counts"
                ),
                Event.registration_open_time.label("event_registration_open_time"),
                Event.registration_close_time.label("event_registration_close_time"),
                Event.status.label("event_status"),
                Event.visibility.label("event_visibility"),
                Event.main_leader_id.label("event_main_leader_id"),
                EventType.name.label("event_type_name"),
                ActivityType.name.label("event_activity_type_name"),
            )
            .select_from(Registration)
            .join(User, Registration.user_id == User.id, isouter=True)
            .join(Event, Registration.event_id == Event.id, isouter=True)
            .join(EventType, Event.event_type_id == EventType.id, isouter=True)
            .join(
                event_activity_types,
                event_activity_types.c.event_id == Event.id,
                isouter=True,
            )
            .join(
                ActivityType,
                event_activity_types.c.activity_id == ActivityType.id,
                isouter=True,
            )
            .where(*self._event_conditions())
            .order_by(Registration.id, ActivityType.id)
        )

    def leader_query(self):
        """Builds the event leaders export query.

        :return: The SQLAlchemy select statement.
        """
        return (
            select(
                event_leaders.c.event_id.label("event_id"),
                event_leaders.c.user_id.label("leader_user_id"),
                (User.first_name + " " + User.last_name).label("leader_name"),
                User.license_category,
                User.type.label("user_type"),
                User.gender,
                Event.title.label("event_title"),
                Event.start.label("event_start"),
                Event.end.label("event_end"),
                Event.num_slots.label("event_num_slots"),
                Event.num_online_slots.label("event_num_online_slots"),
                Event.num_waiting_list.label("event_num_waiting_list"),
                Event.include_leaders_in_counts.label(
                    "event_include_leaders_in_counts"
                ),
                Event.registration_open_time.label("event_registration_open_time"),
                Event.registration_close_time.label("event_registration_close_time"),
                Event.status.label("event_status"),
                Event.visibility.label("event_visibility"),
                Event.main_leader_id.label("event_main_leader_id"),
                EventType.name.label("event_type_name"),
                ActivityType.name.label("event_activity_type_name"),
            )
            .select_from(event_leaders)
            .join(User, event_leaders.c.user_id == User.id, isouter=True)
            .join(Event, event_leaders.c.event_id == Event.id, isouter=True)
            .join(EventType, Event.event_type_id == EventType.id, isouter=True)
            .join(
                event_activity_types,
                event_activity_types.c.event_id == Event.id,
                isouter=True,
            )
            .join(
                ActivityType,
                event_activity_types.c.activity_id == ActivityType.id,
                isouter=True,
            )
            .where(*self._event_conditions())
            .order_by(
                event_leaders.c.event_id, event_leaders.c.user_id, ActivityType.id
            )
        )

    def download_name(self) -> str:
        """Builds the zip file name.

        :return: The file name.
        """
        club_name = _club_file_identifier()
        year = self.year if self.year is not None else "all"
        timestamp = current_time().strftime("%Y%m%d-%H%M%S")
        return f"export_{club_name}_{year}_{timestamp}.zip"

    @staticmethod
    def _write_csv(query, path: str) -> int:
        """Executes a query and writes its result to a csv file.

        :param query: The SQLAlchemy select statement.
        :param path: The path of the csv file to write.
        :return: The number of written rows.
        """
        result = db.session.execute(query)
        count = 0
        with open(path, "w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.writer(csv_file, delimiter=";")
            writer.writerow(list(result.keys()))
            for row in result:
                writer.writerow([_csv_value(value) for value in row])
                count += 1
        return count

    def export(self) -> DatabaseExport:
        """Builds the csv files and bundles them into a zip file.

        The caller is responsible for calling
        :py:meth:`DatabaseExport.cleanup` on the returned object once the
        response has been sent.

        :return: The export result.
        """
        tmpdir = tempfile.mkdtemp(prefix="collectives_export_")
        download_name = self.download_name()
        try:
            files = (
                ("registrations.csv", self.registration_query()),
                ("leaders.csv", self.leader_query()),
            )
            row_counts = {}
            for filename, query in files:
                row_counts[filename] = self._write_csv(
                    query, os.path.join(tmpdir, filename)
                )

            zip_path = os.path.join(tmpdir, download_name)
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for filename, _ in files:
                    archive.write(os.path.join(tmpdir, filename), arcname=filename)
        except Exception:
            shutil.rmtree(tmpdir, ignore_errors=True)
            raise

        return DatabaseExport(zip_path, download_name, tmpdir, row_counts)
