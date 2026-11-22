"""Tests for the import of competency badges from FFCAM extranet exports."""

from datetime import date
from io import BytesIO

import openpyxl
from bs4 import BeautifulSoup
from flask_login import login_user

from collectives.models import ActivityType, BadgeCustomLevel, BadgeIds, db
from collectives.utils import badge_import
from tests import utils
from tests.fixtures.misc import (
    custom_skill,
    custom_skill_with_activity_type,
    custom_skill_with_expiry,
)

HEADER = (
    "N° licence",
    "Adhérent",
    "Club",
    "Territoire",
    "Activité",
    "Nom de l'activité",
    "Groupe de compétences",
    "Niveau de pratique",
    "Date de validation",
    "Transversal",
    "Validé par",
    "Origine",
)


def make_export(rows: list[tuple]) -> BytesIO:
    """Builds an extranet export.

    :param rows: list of (license, skill, date, validator)
    :return: the ``.xlsx`` file content
    """
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(HEADER)
    for license_number, skill, day, grantor in rows:
        sheet.append(
            (license_number, "X", 7400, None, None, None, skill, None, day, 1, grantor)
        )
    content = BytesIO()
    workbook.save(content)
    content.seek(0)
    return content


PRACTITIONER_HEADER = (
    "N° licence",
    "Adhérent",
    "Club",
    "Territoire",
    "Activité",
    "Nom de l'activité",
    "Niveau de pratique",
    "Date de validation",
)


def make_practitioner_export(rows: list[tuple]) -> BytesIO:
    """Builds an extranet export of practitioner levels, which has no validator.

    :param rows: list of (license, level, date); licenses are stored as numbers
    :return: the ``.xlsx`` file content
    """
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(PRACTITIONER_HEADER)
    for license_number, level, day in rows:
        sheet.append((int(license_number), "X", 7400, None, "SN", "NEIGE", level, day))
    content = BytesIO()
    workbook.save(content)
    content.seek(0)
    return content


def add_practitioner_levels(activity_name: str, names: dict[int, str]) -> int:
    """Gives custom names to practitioner levels of an activity.

    :param names: custom name by level
    :return: id of the activity
    """
    activity = ActivityType.query.filter_by(name=activity_name).first()
    for level, name in names.items():
        db.session.add(
            BadgeCustomLevel(
                badge_id=BadgeIds.Practitioner,
                level=level,
                activity_id=activity.id,
                name=name,
                abbrev=name[:3],
            )
        )
    db.session.commit()
    BadgeIds.levels.expire_all()
    return activity.id


def upload_export(client, content: BytesIO):
    """Uploads an export through the competency badge add form.

    :return: the response
    """
    response = client.get("/activity_supervision/competency_badge_holders/")
    data = utils.load_data_from_form(response.text, "extranet-import-form")
    data["export_file"] = (content, "export.xlsx")
    return client.post(
        "/activity_supervision/competency_badge/import/upload", data=data
    )


def mapping_form_data(text: str) -> tuple[dict, dict]:
    """Extracts the mapping form of the import page.

    :return: the form data, and for each competency group its select field name
        and available option labels by value
    """
    soup = BeautifulSoup(text, features="lxml")
    form = soup.find("form", action="/activity_supervision/competency_badge/import")
    data = {
        i["name"]: i.get("value", "") for i in form.select("input") if "name" in i.attrs
    }
    selects = {}
    for select in form.select("select"):
        skill = form.find("label", attrs={"for": select["id"]}).text
        options = {o.get("value", ""): o.text for o in select.select("option")}
        selected = select.find("option", selected=True)
        data[select["name"]] = selected.get("value", "") if selected else ""
        selects[skill] = (select["name"], options)
    return data, selects


def test_normalize():
    """Names are compared regardless of accents, case and punctuation"""
    assert badge_import.normalize(" Anne-Cécile  D'Arc ") == "ANNE CECILE D ARC"
    assert badge_import.normalize("FRANÇOIS") == "FRANCOIS"
    assert badge_import.normalize(None) == ""


def test_match_grantors(app, user1, user2, user3):
    """Validators are matched to a single user, in either name order"""
    user3.first_name = user2.first_name
    user3.last_name = user2.last_name
    db.session.commit()

    full_name = f"{user1.first_name} {user1.last_name}".upper()
    reversed_name = f"{user1.last_name} {user1.first_name}"
    duplicate = f"{user2.first_name} {user2.last_name}"
    names = [full_name, full_name, reversed_name, duplicate, "Nobody Here"]
    names += ["Attribué par migration", None]

    matches = badge_import.match_grantors(names)

    assert matches[full_name].status == badge_import.GrantorStatus.Matched
    assert matches[full_name].user == user1
    assert matches[full_name].count == 2
    assert matches[reversed_name].user == user1
    assert matches[duplicate].status == badge_import.GrantorStatus.Ambiguous
    assert set(matches[duplicate].users) == {user2, user3}
    assert matches["Nobody Here"].status == badge_import.GrantorStatus.NotFound
    assert (
        matches["Attribué par migration"].status
        == badge_import.GrantorStatus.NotAPerson
    )
    assert None not in matches


def test_parse_export():
    """Rows are read by header names; invalid lines are reported"""
    content = make_export(
        [
            ("740020149132", "Skill A", "21/11/2024", "Someone"),
            (740020149133, "Skill B", None, None),
            ("740020149134", "Skill A", "not a date", None),
            ("740020149135", None, "21/11/2024", None),
            (None, None, None, None),
        ]
    )

    parsed = badge_import.parse_export(content)

    assert [row.license for row in parsed.rows] == ["740020149132", "740020149133"]
    assert parsed.rows[0].attribution_date == date(2024, 11, 21)
    assert parsed.rows[0].grantor == "Someone"
    assert parsed.rows[1].attribution_date is None
    assert parsed.groups() == ["Skill A", "Skill B"]
    assert parsed.group_label == "Groupe de compétences"
    assert len(parsed.errors) == 2


def test_upload_invalid_file(supervisor_client):
    """A file which is not an extranet export is rejected"""
    response = upload_export(supervisor_client, BytesIO(b"license;date\n1;2\n"))
    assert response.status_code == 302


def test_extranet_form_only_on_competency_page(supervisor_client):
    """The extranet import is only offered for competency badges"""
    response = supervisor_client.get("/activity_supervision/competency_badge_holders/")
    assert 'id="extranet-import-form"' in response.text
    response = supervisor_client.get("/activity_supervision/volunteers/")
    assert 'id="extranet-import-form"' not in response.text


def test_excel_file_rejected_by_csv_import(supervisor_client, user1, custom_skill):
    """An extranet export uploaded as a CSV file is rejected, whatever its name"""
    content = make_export([(user1.license, custom_skill.name, "21/11/2024", None)])

    response = supervisor_client.get("/activity_supervision/competency_badge_holders/")
    data = utils.load_data_from_form(response.text, "basic_form")
    data["badge_id"] = str(int(BadgeIds.Skill))
    data["level"] = custom_skill.level
    data["activity_id"] = "0"
    data["csv_file"] = (content, "renamed.csv")
    response = supervisor_client.post(
        "/activity_supervision/competency_badge/add",
        data=data,
        follow_redirects=True,
    )

    assert "accepte que les fichiers CSV" in response.text
    assert len(user1.badges) == 0


def test_extranet_import(
    supervisor_client,
    supervisor_user,
    user1,
    user2,
    user3,
    custom_skill,
    custom_skill_with_expiry,
    custom_skill_with_activity_type,
):
    """A supervisor imports an export, mapping competency groups to badges"""
    grantor = f"{user3.first_name} {user3.last_name}".upper()
    content = make_export(
        [
            (user1.license, custom_skill.name, "21/11/2024", grantor),
            (user2.license, custom_skill.name, "21/11/2024", "Attribué par migration"),
            (user1.license, "Some other skill", "01/02/2025", grantor),
            (user2.license, "Ignored skill", "01/02/2025", grantor),
            ("999999999999", custom_skill.name, "01/02/2025", "Unknown Person"),
        ]
    )

    response = upload_export(supervisor_client, content)
    assert response.status_code == 200
    assert "Unknown Person" in response.text
    assert "999999999999" in response.text

    data, selects = mapping_form_data(response.text)
    assert set(selects) == {custom_skill.name, "Some other skill", "Ignored skill"}

    # The skill with the same name is preselected, others are ignored by default
    skill_field, options = selects[custom_skill.name]
    assert options[data[skill_field]].startswith(custom_skill.name)
    assert data[selects["Ignored skill"][0]] == badge_import.IGNORE_CHOICE

    # Only badges the supervisor (of Alpinisme) may grant are offered
    canyon = ActivityType.query.filter_by(name="Canyon").first()
    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    assert not any(value.endswith(f":{canyon.id}") for value in options)
    practitioner = badge_import.BadgeTarget(BadgeIds.Practitioner, 2, alpinisme.id)
    assert practitioner.encode() in options

    data[selects["Some other skill"][0]] = practitioner.encode()
    response = supervisor_client.post(
        "/activity_supervision/competency_badge/import", data=data
    )
    assert response.status_code == 200
    assert "1 ligne(s) non importée(s)" in response.text
    assert "1 ligne(s) d'adhérents sans compte" in response.text

    assert len(user1.badges) == 2
    skill_badge = next(b for b in user1.badges if b.badge_id == BadgeIds.Skill)
    assert skill_badge.level == custom_skill.level
    assert skill_badge.grantor == user3
    practitioner_badge = next(
        b for b in user1.badges if b.badge_id == BadgeIds.Practitioner
    )
    assert practitioner_badge.level == 2
    assert practitioner_badge.activity_id == alpinisme.id

    # Validators not matched to a user fall back to the importing supervisor
    assert len(user2.badges) == 1
    assert user2.badges[0].grantor == supervisor_user


def test_extranet_import_rejects_forbidden_badge(
    supervisor_client, user1, custom_skill
):
    """A badge the supervisor may not grant cannot be forced"""
    content = make_export([(user1.license, custom_skill.name, "21/11/2024", None)])
    response = upload_export(supervisor_client, content)
    data, selects = mapping_form_data(response.text)

    canyon = ActivityType.query.filter_by(name="Canyon").first()
    forbidden = badge_import.BadgeTarget(BadgeIds.Practitioner, 2, canyon.id)
    data[selects[custom_skill.name][0]] = forbidden.encode()

    response = supervisor_client.post(
        "/activity_supervision/competency_badge/import", data=data
    )
    assert response.status_code == 200
    assert len(user1.badges) == 0


def test_extranet_import_rejects_tampered_payload(
    supervisor_client, user1, custom_skill
):
    """The rows carried between stages cannot be modified"""
    content = make_export([(user1.license, custom_skill.name, "21/11/2024", None)])
    response = upload_export(supervisor_client, content)
    data, _ = mapping_form_data(response.text)
    data["payload"] = data["payload"][:-2] + "xx"

    response = supervisor_client.post(
        "/activity_supervision/competency_badge/import", data=data
    )
    assert response.status_code == 302
    assert len(user1.badges) == 0


def test_parse_practitioner_export():
    """Practitioner level exports are read from their own column"""
    content = make_practitioner_export(
        [("740020149132", "INITIE en ski de randonnée", "05/02/2026")]
    )

    parsed = badge_import.parse_export(content)

    assert parsed.group_label == "Niveau de pratique"
    assert parsed.groups() == ["INITIE en ski de randonnée"]
    assert parsed.rows[0].license == "740020149132"
    assert parsed.rows[0].grantor is None


def test_suggest_practitioner_level(app, supervisor_user):
    """Practitioner levels are suggested by activity and custom level name"""
    activity_id = add_practitioner_levels("Alpinisme", {1: "Initié"})

    with app.test_request_context():
        login_user(supervisor_user)
        initie = badge_import.BadgeTarget(BadgeIds.Practitioner, 1, activity_id)
        assert badge_import.suggest_target("INITIE en alpinisme") == initie.encode()
        # Unsupervised activity, or level keeping its default name
        ignore = badge_import.IGNORE_CHOICE
        assert badge_import.suggest_target("INITIE en canyon") == ignore
        assert badge_import.suggest_target("PERFECTIONNE en alpinisme") == ignore


def test_practitioner_import(supervisor_client, supervisor_user, user1, user2):
    """Only the highest practitioner level of a member is granted"""
    activity_id = add_practitioner_levels("Alpinisme", {1: "Initié", 2: "Perfectionné"})
    content = make_practitioner_export(
        [
            (user1.license, "PERFECTIONNE en alpinisme", "01/10/2025"),
            (user1.license, "INITIE en alpinisme", "22/03/2026"),
            (user2.license, "INITIE en alpinisme", "07/01/2025"),
        ]
    )

    response = upload_export(supervisor_client, content)
    assert response.status_code == 200
    assert "Niveau de pratique" in response.text
    assert "le fichier n&#39;en indique pas" in response.text.replace("'", "&#39;")

    data, selects = mapping_form_data(response.text)
    for group, level in (("INITIE en alpinisme", 1), ("PERFECTIONNE en alpinisme", 2)):
        target = badge_import.BadgeTarget(BadgeIds.Practitioner, level, activity_id)
        assert data[selects[group][0]] == target.encode()

    response = supervisor_client.post(
        "/activity_supervision/competency_badge/import", data=data
    )
    assert response.status_code == 200
    assert "1 ligne(s) remplacée(s) par un niveau supérieur" in response.text
    assert "non importée(s)</summary>" not in response.text

    assert [(b.badge_id, b.level, b.activity_id) for b in user1.badges] == [
        (BadgeIds.Practitioner, 2, activity_id)
    ]
    assert user1.badges[0].grantor == supervisor_user
    assert [b.level for b in user2.badges] == [1]
