"""Module to test raw database export"""

# pylint: disable=unused-argument

import csv
import io
import os
import zipfile
from datetime import date

from collectives.models import ActivityType, Configuration, EventType
from collectives.utils.export import DatabaseExportService
from collectives.utils.time import get_ffcam_year

REGISTRATION_COLUMNS = (
    "registration_id",
    "event_id",
    "registration_status",
    "registration_level",
    "registration_is_self",
    "registration_time",
    "user_id",
    "user_name",
    "license_category",
    "user_type",
    "gender",
    "event_title",
    "event_start",
    "event_end",
    "event_num_slots",
    "event_num_online_slots",
    "event_num_waiting_list",
    "event_include_leaders_in_counts",
    "event_registration_open_time",
    "event_registration_close_time",
    "event_status",
    "event_visibility",
    "event_main_leader_id",
    "event_type_name",
    "event_activity_type_name",
)

LEADER_COLUMNS = (
    "event_id",
    "leader_user_id",
    "leader_name",
    "license_category",
    "user_type",
    "gender",
    "event_title",
    "event_start",
    "event_end",
    "event_num_slots",
    "event_num_online_slots",
    "event_num_waiting_list",
    "event_include_leaders_in_counts",
    "event_registration_open_time",
    "event_registration_close_time",
    "event_status",
    "event_visibility",
    "event_main_leader_id",
    "event_type_name",
    "event_activity_type_name",
)


def _current_year() -> int:
    """Returns the current FFCAM year."""
    return get_ffcam_year(date.today())


def _read_csv(archive: zipfile.ZipFile, name: str) -> list:
    """Reads a csv file from a zip archive."""
    with archive.open(name) as csv_file:
        reader = csv.DictReader(
            io.TextIOWrapper(csv_file, encoding="utf-8-sig"), delimiter=";"
        )
        return list(reader)


def test_registration_query_columns(app):
    """The registration query only selects the approved columns."""
    service = DatabaseExportService()
    assert (
        tuple(service.registration_query().selected_columns.keys())
        == REGISTRATION_COLUMNS
    )


def test_leader_query_columns(app):
    """The leader query only selects the approved columns."""
    service = DatabaseExportService()
    assert tuple(service.leader_query().selected_columns.keys()) == LEADER_COLUMNS


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


def test_export_button_visible_for_admin(admin_client, stats_env):
    """The export button is displayed for admins."""
    response = admin_client.get(f"/stats?year={_current_year()}")
    assert response.status_code == 200
    assert "Export base de données" in response.text


def test_export_button_hidden_for_non_admin(leader_client, stats_env):
    """The export button is hidden for non-admin users."""
    response = leader_client.get(f"/stats?year={_current_year()}")
    assert response.status_code == 200
    assert "Export base de données" not in response.text
