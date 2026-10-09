"""Module to test raw database export"""

# pylint: disable=unused-argument

import csv
import io
import zipfile
from datetime import date

from collectives.models import ActivityType, EventType
from collectives.utils.export import (
    LEADER_COLUMNS,
    REGISTRATION_COLUMNS,
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
    columns = set(REGISTRATION_COLUMNS) | set(LEADER_COLUMNS)
    assert columns.isdisjoint(PII_COLUMNS), columns & PII_COLUMNS


def test_export_creates_zip(stats_env):
    """The export bundles both csv files into an in-memory zip."""
    export = DatabaseExportService(year=_current_year()).export()

    assert set(export.row_counts) == {"registrations.csv", "leaders.csv"}
    assert export.row_counts["registrations.csv"] > 0
    assert export.row_counts["leaders.csv"] > 0

    with zipfile.ZipFile(export.stream) as archive:
        assert sorted(archive.namelist()) == [
            "leaders.csv",
            "registrations.csv",
        ]
        with archive.open("registrations.csv") as csv_file:
            content = csv_file.read().decode("utf-8-sig")
    assert content.startswith("registration_id;event_id;")


def test_export_includes_all_event_statuses(stats_env, draft_event, cancelled_event):
    """Unlike statistics, the export includes draft and cancelled events."""
    export = DatabaseExportService(year=_current_year()).export()
    with zipfile.ZipFile(export.stream) as archive:
        leaders = _read_csv(archive, "leaders.csv")

    titles = {row["event_title"] for row in leaders}
    assert draft_event.title in titles
    assert cancelled_event.title in titles


def test_export_respects_event_type_filter(stats_env):
    """The event type filter restricts the exported events."""
    party = EventType.query.filter_by(name="Soirée").first()
    export = DatabaseExportService(
        year=_current_year(), event_type_ids=[party.id]
    ).export()
    with zipfile.ZipFile(export.stream) as archive:
        leaders = _read_csv(archive, "leaders.csv")

    assert leaders
    assert {row["event_type_name"] for row in leaders} == {"Soirée"}


def test_export_respects_activity_filter(stats_env):
    """The activity filter keeps all rows of events having the activity."""
    canyon = ActivityType.query.filter_by(name="Canyon").first()
    export = DatabaseExportService(year=_current_year(), activity_id=canyon.id).export()
    with zipfile.ZipFile(export.stream) as archive:
        leaders = _read_csv(archive, "leaders.csv")

    assert leaders
    assert "Canyon" in {row["event_activity_type_name"] for row in leaders}


def test_export_concatenates_user_name(stats_env, user1):
    """The user name column is first and last name concatenated with a space."""
    export = DatabaseExportService(year=_current_year()).export()
    with zipfile.ZipFile(export.stream) as archive:
        rows = _read_csv(archive, "registrations.csv")

    names = {row["user_name"] for row in rows}
    assert f"{user1.first_name} {user1.last_name}" in names


def test_download_name(stats_env):
    """The zip name follows the export_<year>_<timestamp>.zip pattern."""
    name = DatabaseExportService(year=_current_year()).export().download_name
    assert name.startswith("export_")
    assert f"_{_current_year()}_" in name
    assert name.endswith(".zip")


def test_database_export_endpoint_admin(admin_client, stats_env):
    """An admin can download the database export as a zip."""
    response = admin_client.get(
        f"/stats?database=1&year={_current_year()}&activity_id=999999"
    )
    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert ".zip" in response.headers["Content-Disposition"]

    with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
        assert sorted(archive.namelist()) == ["leaders.csv", "registrations.csv"]


def test_database_export_endpoint_non_admin(leader_client, stats_env):
    """A non-admin user cannot download the database export."""
    response = leader_client.get(
        f"/stats?database=1&year={_current_year()}&activity_id=999999"
    )
    assert response.status_code == 403


def test_export_button_hidden_for_non_admin(leader_client, stats_env):
    """The export button is hidden for non-admin users."""
    response = leader_client.get(f"/stats?year={_current_year()}")
    assert response.status_code == 200
    assert "Export base de données" not in response.text
