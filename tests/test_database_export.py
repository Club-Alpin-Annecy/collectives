"""Module to test raw database export"""

# pylint: disable=unused-argument

import csv
import io
import zipfile
from datetime import date

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.forms.export import DatabaseExportForm
from collectives.models import ActivityType
from collectives.utils.export import (
    DBEXPORT_LEADER_COLUMNS,
    DBEXPORT_LEADERS_CSV,
    DBEXPORT_REGISTRATION_COLUMNS,
    DBEXPORT_REGISTRATIONS_CSV,
    DatabaseExportService,
)
from collectives.utils.time import get_ffcam_year


def _current_year() -> int:
    """Returns the current FFCAM year."""
    return get_ffcam_year(date.today())


#: Personal data columns that must never be part of the raw database export.
PII_COLUMNS = {
    "email",
    "phone",
    "date_of_birth",
    "license",
    "password",
    "avatar",
    "emergency_contact_name",
    "emergency_contact_phone",
}


def _read_csv(archive: zipfile.ZipFile, name: str) -> list:
    """Reads a csv file from a zip archive."""
    with archive.open(name) as csv_file:
        reader = csv.DictReader(
            io.TextIOWrapper(csv_file, encoding="utf-8-sig"), delimiter=";"
        )
        return list(reader)


def test_export_excludes_pii_columns():
    """The export columns must not include any personal data column."""
    columns = set(DBEXPORT_REGISTRATION_COLUMNS) | set(DBEXPORT_LEADER_COLUMNS)
    assert columns.isdisjoint(PII_COLUMNS), columns & PII_COLUMNS


def test_export_creates_zip(stats_env):
    """The export bundles both csv files into an in-memory zip."""
    export = DatabaseExportService(year=_current_year()).export()

    assert set(export.row_counts) == {DBEXPORT_REGISTRATIONS_CSV, DBEXPORT_LEADERS_CSV}
    assert export.row_counts[DBEXPORT_REGISTRATIONS_CSV] > 0
    assert export.row_counts[DBEXPORT_LEADERS_CSV] > 0

    with zipfile.ZipFile(export.stream) as archive:
        assert sorted(
            archive.namelist()
        ) == [  # this may break if csv files are renamed
            DBEXPORT_LEADERS_CSV,
            DBEXPORT_REGISTRATIONS_CSV,
        ]
        with archive.open(DBEXPORT_REGISTRATIONS_CSV) as csv_file:
            content = csv_file.read().decode("utf-8-sig")
    assert content.startswith(
        f"{DBEXPORT_REGISTRATION_COLUMNS[0]};{DBEXPORT_REGISTRATION_COLUMNS[1]};"
    )


def test_export_includes_all_event_statuses(stats_env, draft_event, cancelled_event):
    """Unlike statistics, the export includes draft and cancelled events."""
    export = DatabaseExportService(year=_current_year()).export()
    with zipfile.ZipFile(export.stream) as archive:
        leaders = _read_csv(archive, DBEXPORT_LEADERS_CSV)

    titles = {row[str(DBEXPORT_LEADER_COLUMNS[6])] for row in leaders}
    assert draft_event.title in titles
    assert cancelled_event.title in titles


def test_export_respects_activity_filter(stats_env):
    """The activity filter keeps all rows of events having the activity."""
    canyon = ActivityType.query.filter_by(name="Canyon").first()
    export = DatabaseExportService(year=_current_year(), activity_id=canyon.id).export()
    with zipfile.ZipFile(export.stream) as archive:
        leaders = _read_csv(archive, DBEXPORT_LEADERS_CSV)

    assert leaders
    assert "Canyon" in {row["Activité"] for row in leaders}


def test_export_concatenates_user_name(stats_env, user1):
    """The user name column is first and last name concatenated with a space."""
    export = DatabaseExportService(year=_current_year()).export()
    with zipfile.ZipFile(export.stream) as archive:
        rows = _read_csv(archive, DBEXPORT_REGISTRATIONS_CSV)

    names = {row["Participant"] for row in rows}
    assert f"{user1.first_name} {user1.last_name}" in names


def test_export_form_defaults_to_all_activities(stats_env):
    """The activity filter defaults to the "all activities" choice."""
    form = DatabaseExportForm()
    assert form.activity_id.data == ActivityTypeSelectionForm.ALL_ACTIVITIES


def test_database_export_page_admin(admin_client, stats_env):
    """An admin can open the database export filter page."""
    response = admin_client.get("/activity_supervision/database_export")
    assert response.status_code == 200
    assert "Export de la base de données" in response.text


def test_database_export_page_non_admin(supervisor_client, stats_env):
    """A non-admin supervisor cannot open the database export page."""
    response = supervisor_client.get("/activity_supervision/database_export")
    assert response.status_code == 403


def test_database_export_page_president(president_client, stats_env):
    """A president (activity manager) can open the export page."""
    response = president_client.get("/activity_supervision/database_export")
    assert response.status_code == 200


def test_database_export_endpoint_president(president_client, stats_env):
    """A president can download the database export as a zip."""
    response = president_client.post(
        "/activity_supervision/database_export",
        data={
            "year": _current_year(),
            "activity_id": ActivityTypeSelectionForm.ALL_ACTIVITIES,
        },
    )
    assert response.status_code == 200
    assert response.mimetype == "application/zip"


def test_database_export_endpoint_admin(admin_client, stats_env):
    """An admin can download the database export as a zip."""
    response = admin_client.post(
        "/activity_supervision/database_export",
        data={
            "year": _current_year(),
            "activity_id": ActivityTypeSelectionForm.ALL_ACTIVITIES,
        },
    )
    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert ".zip" in response.headers["Content-Disposition"]

    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert sorted(archive.namelist()) == [
            DBEXPORT_LEADERS_CSV,
            DBEXPORT_REGISTRATIONS_CSV,
        ]


def test_database_export_endpoint_non_admin(supervisor_client, stats_env):
    """A non-admin supervisor cannot download the database export."""
    response = supervisor_client.post(
        "/activity_supervision/database_export",
        data={
            "year": _current_year(),
            "activity_id": ActivityTypeSelectionForm.ALL_ACTIVITIES,
        },
    )
    assert response.status_code == 403


def test_export_button_hidden_for_non_admin(supervisor_client, stats_env):
    """The export button is hidden for non-admin users."""
    response = supervisor_client.get("/activity_supervision/index")
    assert response.status_code == 200
    assert "Export base de données" not in response.text


def test_export_button_visible_for_admin(admin_client, stats_env):
    """The export button is visible for admin users."""
    response = admin_client.get("/activity_supervision/index")
    assert response.status_code == 200
    assert "Export base de données" in response.text
