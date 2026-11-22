"""Tests for the import of badges from files: CSV files and FFCAM extranet exports."""

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


def upload_file(
    client,
    content: BytesIO,
    filename: str = "export.xlsx",
    page: str = "competency_badge_holders/",
    add_url: str = "competency_badge/add",
    **defaults,
):
    """Uploads a file through the badge add form of a page.

    :param defaults: values of the badge fields of the add form
    :return: the response
    """
    response = client.get(f"/activity_supervision/{page}")
    data = utils.load_data_from_form(response.text, "add-badge-form")
    data.update(defaults)
    data["csv_file"] = (content, filename)
    return client.post(f"/activity_supervision/{add_url}", data=data)


def select_options(text: str, name: str) -> dict[str, str]:
    """:return: the option labels by value of a select field of a page"""
    soup = BeautifulSoup(text, features="lxml")
    return {
        o.get("value", ""): o.text for o in soup.select(f"select[name={name}] option")
    }


def warnings_of(text: str) -> list[str]:
    """:return: the group warnings of a mapping page"""
    soup = BeautifulSoup(text, features="lxml")
    return [warning.text.strip() for warning in soup.select(".group-warning")]


def alpinisme_defaults(level: int = 2) -> dict:
    """:return: add form values for a practitioner level of Alpinisme"""
    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    return {
        "badge_id": str(int(BadgeIds.Practitioner)),
        "activity_id": str(alpinisme.id),
        "level": str(level),
    }


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


def test_parse_excel():
    """Extranet rows are read by header names; invalid lines are reported"""
    content = make_export(
        [
            ("740020149132", "Skill A", "21/11/2024", "Someone"),
            (740020149133, "Skill B", None, None),
            ("740020149134", "Skill A", "not a date", None),
            ("740020149135", None, "21/11/2024", None),
            (None, None, None, None),
        ]
    )

    parsed = badge_import.parse_excel(content)

    assert [row.license for row in parsed.rows] == ["740020149132", "740020149133"]
    assert parsed.rows[0].attribution_date == date(2024, 11, 21)
    assert parsed.rows[0].grantor == "Someone"
    assert parsed.rows[1].attribution_date is None
    assert parsed.groups() == ["Skill A", "Skill B"]
    assert parsed.group_label == "Groupe de compétences"
    assert len(parsed.errors) == 2


def test_parse_practitioner_export():
    """Practitioner level exports are read from their own column"""
    content = make_practitioner_export(
        [("740020149132", "INITIE en ski de randonnée", "05/02/2026")]
    )

    parsed = badge_import.parse_excel(content)

    assert parsed.group_label == "Niveau de pratique"
    assert parsed.groups() == ["INITIE en ski de randonnée"]
    assert parsed.rows[0].license == "740020149132"
    assert parsed.rows[0].grantor is None


def test_parse_csv():
    """CSV rows are grouped by activity and level, with optional validator"""
    content = BytesIO(
        "licence;date;activité;niveau;validé par\n"
        "1;21/11/2024;Alpinisme;Niveau 🔵;Jan Johnston\n"
        "2;;Alpinisme;Niveau 🔵;\n"
        "3;;;;\n"
        "4;not a date;;;\n".encode("utf8")
    )

    parsed = badge_import.parse_csv(content)

    assert [row.license for row in parsed.rows] == ["1", "2", "3"]
    assert parsed.rows[0].grantor == "Jan Johnston"
    assert parsed.rows[0].attribution_date == date(2024, 11, 21)
    assert parsed.groups() == ["Activité : Alpinisme · Niveau : Niveau 🔵", ""]
    assert parsed.hints[""] == badge_import.GroupHint()
    assert len(parsed.errors) == 1

    # Without header: license, date, activity, level
    parsed = badge_import.parse_csv(BytesIO(b"5,2024-11-21,Canyon\n"))
    assert parsed.rows[0].license == "5"
    assert parsed.hints[parsed.rows[0].group].activity == "Canyon"


def test_upload_invalid_excel_file(supervisor_client):
    """An unreadable Excel file is rejected"""
    response = upload_file(supervisor_client, BytesIO(b"PK\x03\x04 not a workbook"))
    assert response.status_code == 302


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
    """A supervisor imports an export, choosing the badge of each group"""
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

    response = upload_file(supervisor_client, content, **alpinisme_defaults(level=2))
    assert response.status_code == 200
    assert "Unknown Person" in response.text
    assert "999999999999" in response.text

    _, data, groups = utils.load_badge_import_form(response.text)
    assert set(groups) == {custom_skill.name, "Some other skill", "Ignored skill"}

    # The skill with the same name is suggested
    badge, activity, level = groups[custom_skill.name]
    assert (data[badge], data[activity], data[level]) == (
        str(int(BadgeIds.Skill)),
        "",
        str(custom_skill.level),
    )
    # Other groups get the default badge of the add form
    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()
    badge, activity, level = groups["Some other skill"]
    assert (data[badge], data[activity], data[level]) == (
        str(int(BadgeIds.Practitioner)),
        str(alpinisme.id),
        "2",
    )

    # Only activities the supervisor (of Alpinisme) may grant badges for
    canyon = ActivityType.query.filter_by(name="Canyon").first()
    assert str(canyon.id) not in select_options(response.text, activity)

    data[groups["Ignored skill"][0]] = ""
    response = supervisor_client.post("/activity_supervision/badges/import", data=data)
    assert response.status_code == 200
    assert "1 ligne(s) ignorée(s) à votre demande" in response.text
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


def test_import_rejects_unauthorized_activity(supervisor_client, user1):
    """A badge for an activity the supervisor does not supervise cannot be forced"""
    canyon = ActivityType.query.filter_by(name="Canyon").first()
    canyon_skill = BadgeCustomLevel(
        badge_id=BadgeIds.Skill,
        level=42,
        activity_id=canyon.id,
        name="Canyon skill",
        abbrev="CS",
    )
    db.session.add(canyon_skill)
    db.session.commit()
    BadgeIds.levels.expire_all()

    content = make_export([(user1.license, "Some skill", "21/11/2024", None)])
    response = upload_file(supervisor_client, content, **alpinisme_defaults())
    _, data, groups = utils.load_badge_import_form(response.text)
    badge, activity, level = groups["Some skill"]

    # Activity choices only list supervised activities
    forced = dict(data, **{activity: str(canyon.id)})
    response = supervisor_client.post(
        "/activity_supervision/badges/import", data=forced
    )
    assert 'id="badge-import-form"' in response.text
    assert len(user1.badges) == 0

    # A skill level specific to another activity is rejected as well
    forced = dict(data, **{badge: str(int(BadgeIds.Skill)), level: "42"})
    response = supervisor_client.post(
        "/activity_supervision/badges/import", data=forced
    )
    assert "Activité non autorisée" in response.text
    assert len(user1.badges) == 0


def test_import_rejects_tampered_payload(supervisor_client, user1, custom_skill):
    """The rows carried between stages cannot be modified"""
    content = make_export([(user1.license, custom_skill.name, "21/11/2024", None)])
    response = upload_file(supervisor_client, content)
    _, data, _ = utils.load_badge_import_form(response.text)
    data["payload"] = data["payload"][:-2] + "xx"

    response = supervisor_client.post("/activity_supervision/badges/import", data=data)
    assert response.status_code == 302
    assert len(user1.badges) == 0


def test_suggest_practitioner_level(app, supervisor_user):
    """Practitioner levels are suggested by activity and custom level name"""
    activity_id = add_practitioner_levels("Alpinisme", {1: "Initié"})
    parsed = badge_import.parse_excel(
        make_practitioner_export(
            [
                ("1", "INITIE en alpinisme", "05/02/2026"),
                ("1", "INITIE en canyon", "05/02/2026"),
                ("1", "PERFECTIONNE en alpinisme", "05/02/2026"),
            ]
        )
    )

    with app.test_request_context():
        login_user(supervisor_user)
        mapping = badge_import.default_mapping(
            parsed,
            badge_import.MappingChoice(),
            [BadgeIds.Practitioner, BadgeIds.Skill],
        )

    initie, canyon, perfectionne = (choice for choice, _ in mapping)
    assert (initie.badge_id, initie.activity_id, initie.level) == (
        BadgeIds.Practitioner,
        activity_id,
        1,
    )
    # Unsupervised activity, or level keeping its default name
    assert canyon.badge_id is None
    assert perfectionne.badge_id is None


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

    response = upload_file(supervisor_client, content)
    assert response.status_code == 200
    assert "Niveau de pratique" in response.text
    assert "le fichier n&#39;en indique pas" in response.text.replace("'", "&#39;")

    _, data, groups = utils.load_badge_import_form(response.text)
    for group, level in (("INITIE en alpinisme", 1), ("PERFECTIONNE en alpinisme", 2)):
        badge, activity, level_field = groups[group]
        assert (data[badge], data[activity], data[level_field]) == (
            str(int(BadgeIds.Practitioner)),
            str(activity_id),
            str(level),
        )

    response = utils.confirm_badge_import(supervisor_client, response)
    assert response.status_code == 200
    assert "1 ligne(s) remplacée(s) par un niveau supérieur" in response.text
    assert "non importée(s)</summary>" not in response.text

    assert [(b.badge_id, b.level, b.activity_id) for b in user1.badges] == [
        (BadgeIds.Practitioner, 2, activity_id)
    ]
    assert user1.badges[0].grantor == supervisor_user
    assert [b.level for b in user2.badges] == [1]


def test_csv_import_with_validators(supervisor_client, user1, user2, user3):
    """CSV files may name validators; unknown levels make their group ignored"""
    levels = BadgeIds.Practitioner.levels()
    csv = (
        "licence;niveau;validé par\n"
        f"{user1.license};{levels[3].name};{user3.first_name} {user3.last_name}\n"
        f"{user2.license};Unknown level;{user3.first_name} {user3.last_name}\n"
    )

    response = upload_file(
        supervisor_client,
        BytesIO(csv.encode("utf8")),
        filename="import.csv",
        **alpinisme_defaults(level=1),
    )
    assert warnings_of(response.text) == ["⚠ Niveau « Unknown level » inconnu"]

    response = utils.confirm_badge_import(supervisor_client, response)
    assert response.status_code == 200

    assert [(b.level, b.grantor) for b in user1.badges] == [(3, user3)]
    assert len(user2.badges) == 0


def test_excel_import_on_volunteers_page(supervisor_client, supervisor_user, user1):
    """Files are imported from every add form, with the badge types of its page"""
    content = make_export([(user1.license, "Some group", "21/11/2024", None)])
    alpinisme = ActivityType.query.filter_by(name="Alpinisme").first()

    response = upload_file(
        supervisor_client,
        content,
        page="volunteers/",
        add_url="volunteers/add",
        activity_id=str(alpinisme.id),
    )
    assert response.status_code == 200
    _, data, groups = utils.load_badge_import_form(response.text)
    badge, activity, _ = groups["Some group"]
    assert select_options(response.text, badge) == {
        "": "Ignorer",
        str(int(BadgeIds.Benevole)): BadgeIds.Benevole.display_name(),
    }
    assert (data[badge], data[activity]) == (
        str(int(BadgeIds.Benevole)),
        str(alpinisme.id),
    )

    response = utils.confirm_badge_import(supervisor_client, response)
    assert response.status_code == 200
    assert [(b.badge_id, b.activity_id) for b in user1.badges] == [
        (BadgeIds.Benevole, alpinisme.id)
    ]
