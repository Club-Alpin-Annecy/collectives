"""Import of competency badges from an FFCAM extranet export.

The FFCAM extranet exports validated competencies as Excel files with one line
per member and validation: "Groupes de compétences" (competency groups) and
"Niveaux de pratique validés" (practitioner levels). Both are handled the same
way; the value of the competency group or practitioner level column is called
the *group* of the line. Importing a file is a three-stage process:

1. the supervisor uploads the file, which is parsed by :py:func:`parse_export`;
2. the supervisor maps each group of the file to a badge they may grant (or
   ignores it), while reviewing diagnostics such as the matching of validators
   to users (see :py:func:`match_grantors`);
3. badges are created or renewed by :py:func:`import_badges`.

Between stages, the parsed rows are carried in a signed form field (see
:py:func:`dump_payload`), so nothing needs to be stored server-side.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import IO, Iterable

import openpyxl
from flask import current_app
from flask_login import current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from collectives.forms.badge import compute_default_expiration_date
from collectives.models import ActivityType, Badge, BadgeIds, User, db
from collectives.utils import time
from collectives.utils.badges import (
    BulkImportReport,
    grant_badge,
    parse_date,
    users_by_license,
)

PAYLOAD_SALT = "competency-badge-import"
""" Salt of the signature of the payload carried between import stages."""

PAYLOAD_MAX_AGE = 3600
""" Validity of the payload carried between import stages, in seconds."""

IGNORE_CHOICE = ""
""" Value of the mapping choice meaning that a group is ignored."""

_COLUMNS = {
    "license": ("nlicence", "licence", "license"),
    "group": ("groupedecompetences", "competence", "niveaudepratique"),
    "date": ("datedevalidation", "date"),
    "grantor": ("validepar",),
}
""" Normalized header prefixes for each column of interest, by priority."""


class BadgeImportError(RuntimeError):
    """Raised when an uploaded export cannot be imported."""


def normalize(text: str | None) -> str:
    """Normalizes a name for comparison purposes.

    Removes accents, case, punctuation and redundant whitespace, so that for
    instance ``"Anne-Cécile  D'Arc"`` and ``"ANNE CECILE D ARC"`` compare equal.

    :param text: the text to normalize
    :return: the normalized text
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text)
    return text.strip().upper()


@dataclass
class ImportRow:
    """A line of the export."""

    line: int
    """ Line number in the spreadsheet (1-based, header included)."""
    license: str
    """ License number of the member."""
    group: str
    """ Competency group or practitioner level of the line."""
    attribution_date: date | None
    """ Date at which the competency was validated, if known."""
    grantor: str | None
    """ Name of the person who validated the competency, if any."""


@dataclass
class ParsedExport:
    """Result of the parsing of an export."""

    rows: list[ImportRow] = field(default_factory=list)
    """ Valid lines of the export."""
    errors: list[str] = field(default_factory=list)
    """ Description of lines which could not be read."""
    group_label: str = "Groupe de compétences"
    """ Header of the group column in the export, for display."""

    def groups(self) -> list[str]:
        """Returns the groups of the export, in order of appearance.

        :return: list of distinct groups
        """
        return list(dict.fromkeys(row.group for row in self.rows))

    def group_counts(self) -> Counter:
        """Returns the number of lines of each group.

        :return: counter of lines by group
        """
        return Counter(row.group for row in self.rows)


def _cell_text(value) -> str:
    """Returns the textual content of a cell.

    Integral floats are converted without decimals, so that license numbers
    stored as numbers are read correctly.

    :param value: cell value
    :return: stripped text of the cell
    """
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def parse_export(stream: IO[bytes]) -> ParsedExport:
    """Parses an FFCAM export of competency groups or practitioner levels.

    The first line must contain the column headers. Required columns are the
    license number ("N° licence") and the group: "Groupe de compétences", or
    else "Niveau de pratique". The validation date ("Date de validation") and
    validator ("Validé par") are optional.

    :param stream: binary stream of the ``.xlsx`` file
    :return: the parsed rows and the description of invalid lines
    :raises BadgeImportError: if the file cannot be read or misses required columns
    """
    try:
        workbook = openpyxl.load_workbook(stream, read_only=True, data_only=True)
    except Exception as err:
        raise BadgeImportError(
            "Le fichier n'est pas un fichier Excel (.xlsx) valide."
        ) from err

    try:
        rows = workbook.active.iter_rows(values_only=True)
        raw_header = next(rows, ())
        header = [normalize(cell).replace(" ", "").lower() for cell in raw_header]

        columns = {}
        for key, prefixes in _COLUMNS.items():
            for prefix in prefixes:
                index = next(
                    (i for i, name in enumerate(header) if name.startswith(prefix)),
                    None,
                )
                if index is not None:
                    columns[key] = index
                    break

        if "license" not in columns or "group" not in columns:
            raise BadgeImportError(
                "Colonnes « N° licence » et « Groupe de compétences » ou « Niveau de "
                "pratique » introuvables sur la première ligne du fichier."
            )

        def cell(row: tuple, key: str):
            """Returns the value of a column of interest, or None"""
            index = columns.get(key)
            if index is None or index >= len(row):
                return None
            return row[index]

        result = ParsedExport(group_label=_cell_text(raw_header[columns["group"]]))
        for line, row in enumerate(rows, start=2):
            license_number = _cell_text(cell(row, "license"))
            group = _cell_text(cell(row, "group"))
            if not license_number and not group:
                continue  # Blank line
            if not license_number or not group:
                result.errors.append(
                    f"Ligne {line} : licence ou {result.group_label} manquant"
                )
                continue
            try:
                attribution_date = parse_date(cell(row, "date"))
            except ValueError as err:
                result.errors.append(f"Ligne {line} : date invalide '{err}'")
                continue

            result.rows.append(
                ImportRow(
                    line=line,
                    license=license_number,
                    group=group,
                    attribution_date=attribution_date,
                    grantor=_cell_text(cell(row, "grantor")) or None,
                )
            )
    finally:
        workbook.close()

    if not result.rows:
        raise BadgeImportError("Le fichier ne contient aucune ligne exploitable.")

    return result


def dump_payload(export: ParsedExport) -> str:
    """Serializes and signs parsed rows, to be carried to the next stage.

    :param export: the parsed export
    :return: a signed, compressed, URL-safe token
    """
    groups = export.groups()
    group_index = {group: i for i, group in enumerate(groups)}
    data = {
        "user": current_user.id,
        "groups": groups,
        "label": export.group_label,
        "errors": export.errors,
        "rows": [
            [
                row.line,
                row.license,
                group_index[row.group],
                row.attribution_date.isoformat() if row.attribution_date else None,
                row.grantor,
            ]
            for row in export.rows
        ],
    }
    return _serializer().dumps(data)


def load_payload(token: str) -> ParsedExport:
    """Verifies and deserializes a token produced by :py:func:`dump_payload`.

    :param token: the signed token
    :return: the parsed export
    :raises BadgeImportError: if the token is invalid, expired or belongs to someone else
    """
    try:
        data = _serializer().loads(token, max_age=PAYLOAD_MAX_AGE)
    except SignatureExpired as err:
        raise BadgeImportError(
            "L'import a expiré, veuillez recharger le fichier."
        ) from err
    except BadSignature as err:
        raise BadgeImportError("Données d'import invalides.") from err

    if data.get("user") != current_user.id:
        raise BadgeImportError("Données d'import invalides.")

    groups = data["groups"]
    return ParsedExport(
        rows=[
            ImportRow(
                line=line,
                license=license_number,
                group=groups[group],
                attribution_date=date.fromisoformat(day) if day else None,
                grantor=grantor,
            )
            for line, license_number, group, day, grantor in data["rows"]
        ],
        errors=data["errors"],
        group_label=data["label"],
    )


def _serializer() -> URLSafeTimedSerializer:
    """:return: the serializer used to sign payloads"""
    return URLSafeTimedSerializer(current_app.secret_key, salt=PAYLOAD_SALT)


class GrantorStatus(Enum):
    """Outcome of the matching of a validator name to a user."""

    Matched = "matched"
    """ A single user matches the name."""
    Ambiguous = "ambiguous"
    """ Several users match the name."""
    NotFound = "not_found"
    """ No user matches the name."""
    NotAPerson = "not_a_person"
    """ The name designates an automatic process, such as a migration."""


@dataclass
class GrantorMatch:
    """Result of the matching of a validator name to a user."""

    name: str
    """ Name as found in the export."""
    status: GrantorStatus
    """ Outcome of the matching."""
    users: list[User] = field(default_factory=list)
    """ Matching users."""
    count: int = 0
    """ Number of lines of the export with this validator."""

    @property
    def user(self) -> User | None:
        """:return: the matched user, if exactly one user matches"""
        if self.status == GrantorStatus.Matched:
            return self.users[0]
        return None


_NOT_A_PERSON = re.compile(r"\b(MIGRATION|AUTOMATIQUE)\b")
""" Pattern of validator names designating an automatic process."""


def match_grantors(names: Iterable[str | None]) -> dict[str, GrantorMatch]:
    """Matches validator names to users.

    Names and user names are normalized (see :py:func:`normalize`). Both
    "first last" and "last first" orders are accepted. A name is only matched if
    a single user corresponds to it.

    :param names: validator names, one per line of the export (may repeat)
    :return: matching result for each distinct non-empty name
    """
    counts = Counter(name for name in names if name)
    if not counts:
        return {}

    index: dict[str, set[int]] = {}
    for user_id, first_name, last_name in db.session.query(
        User.id, User.first_name, User.last_name
    ):
        for key in (f"{first_name} {last_name}", f"{last_name} {first_name}"):
            index.setdefault(normalize(key), set()).add(user_id)

    matches = {}
    for name, count in counts.items():
        key = normalize(name)
        user_ids = index.get(key, set())
        if _NOT_A_PERSON.search(key):
            status = GrantorStatus.NotAPerson
            user_ids = set()
        elif not user_ids:
            status = GrantorStatus.NotFound
        elif len(user_ids) > 1:
            status = GrantorStatus.Ambiguous
        else:
            status = GrantorStatus.Matched
        matches[name] = GrantorMatch(
            name=name,
            status=status,
            users=[db.session.get(User, user_id) for user_id in sorted(user_ids)],
            count=count,
        )
    return matches


def unknown_licenses(rows: Iterable[ImportRow]) -> list[str]:
    """Returns license numbers of the export which match no user.

    :param rows: lines of the export
    :return: sorted list of unknown license numbers
    """
    licenses = {row.license for row in rows}
    return sorted(licenses - users_by_license(licenses).keys())


@dataclass(frozen=True)
class BadgeTarget:
    """A badge a competency group may be mapped to."""

    badge_id: BadgeIds
    """ Type of the badge."""
    level: int
    """ Level of the badge."""
    activity_id: int | None
    """ Activity of the badge, if any."""

    def encode(self) -> str:
        """:return: the value of this target in a select field"""
        activity = "" if self.activity_id is None else self.activity_id
        return f"{int(self.badge_id)}:{self.level}:{activity}"


def grantable_activities() -> list[ActivityType]:
    """:return: activities for which the current user may grant badges"""
    if current_user.is_hotline():
        return ActivityType.get_all_types()
    return current_user.get_supervised_activities()


def badge_targets() -> dict[str, list[tuple[BadgeTarget, str]]]:
    """Lists the badges the current user may grant, grouped for display.

    :return: dict of group name to list of (target, label)
    """
    activities = sorted(grantable_activities(), key=lambda a: a.name)
    activity_ids = {activity.id for activity in activities}

    skills = [
        (
            BadgeTarget(BadgeIds.Skill, level, desc.activity_id),
            f"{desc.name} ({desc.activity_name()})",
        )
        for level, desc in BadgeIds.Skill.levels().items()
        if desc.activity_id is None or desc.activity_id in activity_ids
    ]
    skills.sort(key=lambda item: item[1].lower())

    groups = {}
    if skills:
        groups[BadgeIds.Skill.display_name()] = skills
    for activity in activities:
        levels = BadgeIds.Practitioner.levels(activity_id=activity.id)
        if levels:
            groups[f"{BadgeIds.Practitioner.display_name()} - {activity.name}"] = [
                (BadgeTarget(BadgeIds.Practitioner, level, activity.id), desc.name)
                for level, desc in sorted(levels.items())
            ]
    return groups


def decode_target(value: str) -> BadgeTarget | None:
    """Decodes a select field value into a badge target, checking that the
    current user may grant it.

    :param value: value produced by :py:meth:`BadgeTarget.encode`
    :return: the target, or None for :py:data:`IGNORE_CHOICE`
    :raises BadgeImportError: if the value is invalid or not allowed
    """
    if value == IGNORE_CHOICE:
        return None
    for targets in badge_targets().values():
        for target, _ in targets:
            if target.encode() == value:
                return target
    raise BadgeImportError(f"Badge non autorisé : {value}")


def suggest_target(group: str) -> str:
    """Suggests the badge of a group, when a single grantable badge matches it.

    Names are compared once normalized (see :py:func:`normalize`). A skill
    matches if its name is the group. A practitioner level matches if the group
    contains both the name of its activity and its custom name, such as
    "INITIE en ski de randonnée" for a level named "Initié" of "Ski de
    randonnée"; levels keeping their default name never match.

    :param group: a group of the export
    :return: encoded target, or :py:data:`IGNORE_CHOICE` if none or several match
    """
    key = normalize(group)
    padded_key = f" {key} "
    default_names = BadgeIds.Practitioner.levels(only_defaults=True)

    def matches(target: BadgeTarget) -> bool:
        """Whether the target matches the group"""
        desc = target.badge_id.level(target.level, activity_id=target.activity_id)
        if target.badge_id == BadgeIds.Skill:
            return normalize(desc.name) == key
        default = default_names.get(target.level)
        if default is not None and default.name == desc.name:
            return False
        activity = ActivityType.get(target.activity_id)
        return all(
            f" {normalize(name)} " in padded_key for name in (activity.name, desc.name)
        )

    found = {
        target.encode()
        for targets in badge_targets().values()
        for target, _ in targets
        if matches(target)
    }
    if len(found) == 1:
        return found.pop()
    return IGNORE_CHOICE


def import_badges(
    export: ParsedExport, mapping: dict[str, BadgeTarget | None]
) -> BulkImportReport:
    """Creates or renews badges according to the export.

    Badges are granted with :py:func:`collectives.utils.badges.grant_badge`, as for
    CSV imports. The validator is recorded as grantor when it matches a single
    user; otherwise the importing user is.

    :param export: the parsed export
    :param mapping: badge to grant for each group (None to ignore)
    :return: the report of the import
    """
    report = BulkImportReport()
    rows = [row for row in export.rows if mapping.get(row.group) is not None]
    report.ignored = len(export.rows) - len(rows)

    # For badges with ordered levels, having a level implies having the lower
    # ones: only grant the highest level of each member, badge and activity
    def ordered_key(row: ImportRow) -> tuple | None:
        """Key of rows superseding each other, or None"""
        target = mapping[row.group]
        if not target.badge_id.has_ordered_levels():
            return None
        return (row.license, target.badge_id, target.activity_id)

    highest = {}
    for row in rows:
        key = ordered_key(row)
        if key is not None and (
            key not in highest
            or mapping[highest[key].group].level < mapping[row.group].level
        ):
            highest[key] = row
    kept = [
        row for row in rows if (key := ordered_key(row)) is None or highest[key] is row
    ]
    report.superseded = len(rows) - len(kept)
    rows = kept

    grantors = match_grantors(row.grantor for row in rows)
    users = users_by_license(row.license for row in rows)

    for row in rows:
        target = mapping[row.group]
        user = users.get(row.license)
        if user is None:
            report.unknown_licenses.append(row.license)
            continue

        badge = Badge(
            badge_id=target.badge_id,
            level=target.level,
            activity_id=target.activity_id,
            expiration_date=compute_default_expiration_date(
                badge_id=target.badge_id,
                level=target.level,
                attribution_date=row.attribution_date,
            ),
            creation_time=time.current_time(),
        )

        match = grantors.get(row.grantor)
        try:
            grant_badge(user, badge, report, grantor=match.user if match else None)
        except RuntimeError as err:
            report.errors.append(f"Ligne {row.line} : {user.full_name()} : {err}")

    db.session.commit()
    return report
