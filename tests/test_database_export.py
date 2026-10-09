"""Module to test raw database export"""

# pylint: disable=unused-argument

import csv
import io
import os
import zipfile
from datetime import date

from sqlalchemy.sql.elements import ColumnClause, Label

from collectives.models import ActivityType, Configuration, EventType
from collectives.utils.export import DatabaseExportService
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


def _underlying_columns(expression) -> set:
    """Recursively collects the base column names used by a select expression."""
    if isinstance(expression, Label):
        return _underlying_columns(expression.element)
    if isinstance(expression, ColumnClause):
        return {expression.name} if expression.name else set()
    names = set()
    for child in expression.get_children():
        names |= _underlying_columns(child)
    return names


def _read_csv(archive: zipfile.ZipFile, name: str) -> list:
    """Reads a csv file from a zip archive."""
    with archive.open(name) as csv_file:
        reader = csv.DictReader(
            io.TextIOWrapper(csv_file, encoding="utf-8-sig"), delimiter=";"
        )
        return list(reader)


def test_export_excludes_pii_columns(stats_env):
    """The export queries must not select any personal data column."""
    service = DatabaseExportService(year=_current_year())
    for query in (service.registration_query(), service.leader_query()):
        selected = set()
        for column in query.selected_columns:
            selected |= _underlying_columns(column)
        assert selected.isdisjoint(PII_COLUMNS), selected & PII_COLUMNS


def test_export_creates_zip(stats_env):
    """The export bundles both csv files into a zip and cleans up its temp dir."""
    export = DatabaseExportService(year=_current_year()).export()
    tmpdir = export.tmpdir
    try:
        assert set(export.row_counts) == {"registrations.csv", "leaders.csv"}
        assert export.row_counts["registrations.csv"] > 0
        assert export.row_counts["leaders.csv"] > 0
        assert os.path.exists(export.path)

        with zipfile.ZipFile(export.path) as archive:
            assert sorted(archive.namelist()) == [
                "leaders.csv",
                "registrations.csv",
            ]
            with archive.open("registrations.csv") as csv_file:
                content = csv_file.read().decode("utf-8-sig")
        assert content.startswith("registration_id;event_id;")
    finally:
        export.cleanup()

    assert not os.path.exists(tmpdir)


def test_export_includes_all_event_statuses(stats_env, draft_event, cancelled_event):
    """Unlike statistics, the export includes draft and cancelled events."""
    export = DatabaseExportService(year=_current_year()).export()
    try:
        with zipfile.ZipFile(export.path) as archive:
            leaders = _read_csv(archive, "leaders.csv")
    finally:
        export.cleanup()

    titles = {row["event_title"] for row in leaders}
    assert draft_event.title in titles
    assert cancelled_event.title in titles


def test_export_respects_event_type_filter(stats_env):
    """The event type filter restricts the exported events."""
    party = EventType.query.filter_by(name="Soirée").first()
    export = DatabaseExportService(
        year=_current_year(), event_type_ids=[party.id]
    ).export()
    try:
        with zipfile.ZipFile(export.path) as archive:
            leaders = _read_csv(archive, "leaders.csv")
    finally:
        export.cleanup()

    assert leaders
    assert {row["event_type_name"] for row in leaders} == {"Soirée"}


def test_export_respects_activity_filter(stats_env):
    """The activity filter keeps all rows of events having the activity."""
    canyon = ActivityType.query.filter_by(name="Canyon").first()
    export = DatabaseExportService(year=_current_year(), activity_id=canyon.id).export()
    try:
        with zipfile.ZipFile(export.path) as archive:
            leaders = _read_csv(archive, "leaders.csv")
    finally:
        export.cleanup()

    assert leaders
    assert "Canyon" in {row["event_activity_type_name"] for row in leaders}


def test_export_concatenates_user_name(stats_env, user1):
    """The user name column is first and last name concatenated with a space."""
    export = DatabaseExportService(year=_current_year()).export()
    try:
        with zipfile.ZipFile(export.path) as archive:
            rows = _read_csv(archive, "registrations.csv")
    finally:
        export.cleanup()

    names = {row["user_name"] for row in rows}
    assert f"{user1.first_name} {user1.last_name}" in names


def test_download_name(stats_env):
    """The zip name follows the export_<club>_<year>_<timestamp>.zip pattern."""
    service = DatabaseExportService(year=_current_year())
    name = service.download_name()
    assert name.startswith("export_")
    assert f"_{_current_year()}_" in name
    assert name.endswith(".zip")
    # Spaces and special characters from the club name are stripped.
    assert " " not in name
    assert "NomduClub" in name


def test_download_name_uses_club_prefix(monkeypatch, stats_env):
    """CLUB_PREFIX is used in the file name instead of the club name when set."""
    monkeypatch.setattr(Configuration, "CLUB_PREFIX", "7400")
    name = DatabaseExportService(year=_current_year()).download_name()

    assert "7400" in name
    assert "NomduClub" not in name


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


def test_database_export_cleans_up_temp_files(admin_client, stats_env, monkeypatch):
    """The temporary directory is removed once the response is closed."""
    captured = {}
    original_export = DatabaseExportService.export

    def export(self):
        database_export = original_export(self)
        captured["export"] = database_export
        return database_export

    monkeypatch.setattr(DatabaseExportService, "export", export)

    response = admin_client.get(
        f"/stats?database=1&year={_current_year()}&activity_id=999999"
    )
    response.close()

    assert not os.path.exists(captured["export"].tmpdir)


def test_export_button_hidden_for_non_admin(leader_client, stats_env):
    """The export button is hidden for non-admin users."""
    response = leader_client.get(f"/stats?year={_current_year()}")
    assert response.status_code == 200
    assert "Export base de données" not in response.text
