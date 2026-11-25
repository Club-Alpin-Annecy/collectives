"""Import of badges from a file: a CSV file, or an FFCAM extranet export.

The FFCAM extranet exports validated competencies as Excel files with one line
per member and validation: "Groupes de compétences" (competency groups) and
"Niveaux de pratique validés" (practitioner levels). CSV files have one line per
member, with optional date, activity, level and validator columns.

Lines are grouped by what they tell about the badge to grant: the competency
group or practitioner level of extranet exports, the activity and level columns
of CSV files. Importing a file is a three-stage process:

1. the user uploads the file with the badge add form, whose badge type, activity
   and level are the default badge of the file (see :py:func:`start_import`);
2. the user chooses the badge to grant for each group, pre-filled from the lines
   and the defaults (see :py:func:`default_mapping`), while reviewing
   diagnostics such as unknown licenses or the matching of validators to users
   (see :py:func:`match_grantors`);
3. badges are created or renewed (see :py:func:`confirm_import`).

Between stages, the parsed lines are carried in a signed form field (see
:py:func:`dump_payload`), so nothing needs to be stored server-side.
"""

import codecs
import csv
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import IO, Iterable
from xml.etree.ElementTree import ParseError

import openpyxl
from defusedxml import DefusedXmlException
from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from collectives.forms.badge import (
    BadgeImportMappingForm,
    compute_default_expiration_date,
    is_excel_file,
)
from collectives.models import ActivityType, Badge, BadgeIds, User, db
from collectives.utils import time
from collectives.utils.badges import (
    BulkImportReport,
    grant_badge,
    parse_date,
    users_by_license,
)

PAYLOAD_SALT = "badge-file-import"
""" Salt of the signature of the payload carried between import stages."""

PAYLOAD_MAX_AGE = 3600
""" Validity of the payload carried between import stages, in seconds."""

_EXCEL_COLUMNS = {
    "license": ("nlicence", "licence", "license"),
    "group": ("groupedecompetences", "competence", "niveaudepratique"),
    "date": ("datedevalidation", "date"),
    "grantor": ("validepar",),
}
""" Normalized header prefixes of the columns of extranet exports, by priority."""

_CSV_COLUMNS = {
    "license": ("license", "licence", "nlicence"),
    "date": ("attributiondate", "dateattribution", "datedevalidation", "date"),
    "activity": ("activity", "activite"),
    "level": ("level", "niveau", "niveaudepratique"),
    "grantor": ("validepar", "valideur", "grantor"),
}
""" Normalized header names of the columns of CSV files."""

_CSV_POSITIONS = {"license": 0, "date": 1, "activity": 2, "level": 3}
""" Positions of the columns of CSV files without header."""


class BadgeImportError(RuntimeError):
    """Raised when an uploaded file cannot be imported."""


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


def _header_key(text) -> str:
    """:return: a column header normalized for matching, without spaces"""
    return normalize(text).replace(" ", "").lower()


@dataclass
class ImportRow:
    """A line of the file."""

    line: int
    """ Line number in the file (1-based, header included)."""
    license: str
    """ License number of the member."""
    group: str
    """ What the line tells about the badge to grant (see :py:class:`GroupHint`)."""
    attribution_date: date | None
    """ Date at which the badge was granted, if known."""
    grantor: str | None
    """ Name of the person who granted the badge, if any."""


@dataclass(frozen=True)
class GroupHint:
    """What the lines of a group tell about the badge to grant."""

    text: str | None = None
    """ Competency group or practitioner level of an extranet export."""
    activity: str | None = None
    """ Activity name of a CSV file."""
    level: str | None = None
    """ Level name of a CSV file."""


@dataclass
class ParsedFile:
    """Result of the parsing of a file."""

    rows: list[ImportRow] = field(default_factory=list)
    """ Valid lines of the file."""
    errors: list[str] = field(default_factory=list)
    """ Description of lines which could not be read."""
    group_label: str = ""
    """ Description of the groups of the file, for display."""
    hints: dict[str, GroupHint] = field(default_factory=dict)
    """ Hint of each group. Not carried between stages."""

    def groups(self) -> list[str]:
        """Returns the groups of the file, in order of appearance.

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


def parse_file(file_storage) -> ParsedFile:
    """Parses an uploaded file, either an extranet export or a CSV file.

    :param file_storage: the uploaded file
    :type file_storage: :py:class:`werkzeug.datastructures.FileStorage`
    :return: the parsed lines and the description of invalid lines
    :raises BadgeImportError: if the file cannot be read
    """
    if is_excel_file(file_storage):
        parsed = parse_excel(file_storage.stream)
    else:
        parsed = parse_csv(file_storage.stream)
    if not parsed.rows:
        raise BadgeImportError("Le fichier ne contient aucune ligne exploitable.")
    return parsed


def parse_excel(stream: IO[bytes]) -> ParsedFile:
    """Parses an FFCAM export of competency groups or practitioner levels.

    The first line must contain the column headers. Required columns are the
    license number ("N° licence") and the group: "Groupe de compétences", or
    else "Niveau de pratique". The validation date ("Date de validation") and
    validator ("Validé par") are optional.

    :param stream: binary stream of the ``.xlsx`` file
    :return: the parsed lines and the description of invalid lines
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
        header = [_header_key(cell) for cell in raw_header]

        columns = {}
        for key, prefixes in _EXCEL_COLUMNS.items():
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

        result = ParsedFile(group_label=_cell_text(raw_header[columns["group"]]))
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

            result.hints[group] = GroupHint(text=group)
            result.rows.append(
                ImportRow(
                    line=line,
                    license=license_number,
                    group=group,
                    attribution_date=attribution_date,
                    grantor=_cell_text(cell(row, "grantor")) or None,
                )
            )
    except (DefusedXmlException, ParseError) as err:
        # Sheets are parsed lazily; defusedxml rejects entity declarations,
        # which could otherwise expand to exhaust memory ("billion laughs").
        raise BadgeImportError(
            "Le fichier n'est pas un fichier Excel (.xlsx) valide."
        ) from err
    finally:
        workbook.close()

    return result


def parse_csv(stream: IO[bytes]) -> ParsedFile:
    """Parses a CSV file of members to grant badges to.

    The file may be UTF-8 or Latin-1 encoded, and its columns separated by
    commas or semicolons. Its first line may be a header naming the columns:
    license ("licence"), date ("date"), activity ("activité"), level ("niveau")
    and validator ("validé par"). Without header, columns are the license, the
    date, the activity and the level. Only the license is required.

    Lines are grouped by their activity and level.

    :param stream: binary stream of the file
    :return: the parsed lines and the description of invalid lines
    :raises BadgeImportError: if the file is empty
    """
    sample = stream.read(8192) or b""
    encoding = "utf8"
    try:
        sample_text = sample.decode(encoding)
    except UnicodeDecodeError:
        encoding = "iso-8859-1"
        sample_text = sample.decode(encoding, errors="replace")

    try:
        delimiter = csv.Sniffer().sniff(sample_text, delimiters=";,").delimiter
    except csv.Error:
        delimiter = ";" if sample_text.count(";") > sample_text.count(",") else ","

    stream.seek(0)
    rows = list(csv.reader(codecs.iterdecode(stream, encoding), delimiter=delimiter))
    if not rows:
        raise BadgeImportError("Fichier vide.")

    header = [_header_key(cell) for cell in rows[0]]
    known_names = {name for names in _CSV_COLUMNS.values() for name in names}
    has_header = bool(rows[0]) and (
        any(name in known_names for name in header) or not rows[0][0].strip().isdigit()
    )
    if has_header:
        columns = {
            key: next((i for i, name in enumerate(header) if name in names), None)
            for key, names in _CSV_COLUMNS.items()
        }
    else:
        columns = dict(_CSV_POSITIONS)

    def cell(row: list, key: str) -> str:
        """Returns the stripped value of a column of interest"""
        index = columns.get(key)
        if index is None or index >= len(row):
            return ""
        return row[index].strip()

    result = ParsedFile(group_label="Activité et niveau")
    first_line = 2 if has_header else 1
    for line, row in enumerate(rows[first_line - 1 :], start=first_line):
        license_number = cell(row, "license")
        if not license_number:
            continue
        try:
            attribution_date = parse_date(cell(row, "date"))
        except ValueError as err:
            result.errors.append(f"Ligne {line} : date invalide '{err}'")
            continue

        hint = GroupHint(
            activity=cell(row, "activity") or None, level=cell(row, "level") or None
        )
        group = " · ".join(
            f"{label} : {value}"
            for label, value in (("Activité", hint.activity), ("Niveau", hint.level))
            if value
        )
        result.hints[group] = hint
        result.rows.append(
            ImportRow(
                line=line,
                license=license_number,
                group=group,
                attribution_date=attribution_date,
                grantor=cell(row, "grantor") or None,
            )
        )
    return result


@dataclass
class ImportContext:
    """Where and how a file is imported. Carried between stages."""

    badge_types: list[BadgeIds]
    """ Badge types which may be granted from the page."""
    expiration_date: date | None
    """ Expiration date of badges without attribution date, if chosen by the user.
    Otherwise, it is computed from the badge level."""
    back_url: str
    """ URL of the page the import was started from."""
    extends: str
    """ Template the import pages extend."""


def dump_payload(parsed: ParsedFile, context: ImportContext, warnings: list) -> str:
    """Serializes and signs parsed lines, to be carried to the next stage.

    :param parsed: the parsed file
    :param context: the import context
    :param warnings: warning of each group (see :py:func:`default_mapping`)
    :return: a signed, compressed, URL-safe token
    """
    groups = parsed.groups()
    group_index = {group: i for i, group in enumerate(groups)}
    data = {
        "user": current_user.id,
        "groups": groups,
        "warnings": warnings,
        "label": parsed.group_label,
        "errors": parsed.errors,
        "rows": [
            [
                row.line,
                row.license,
                group_index[row.group],
                row.attribution_date.isoformat() if row.attribution_date else None,
                row.grantor,
            ]
            for row in parsed.rows
        ],
        "types": [int(badge_id) for badge_id in context.badge_types],
        "expiration": (
            context.expiration_date.isoformat() if context.expiration_date else None
        ),
        "back": context.back_url,
        "extends": context.extends,
    }
    return _serializer().dumps(data)


def load_payload(token: str) -> tuple[ParsedFile, ImportContext, list]:
    """Verifies and deserializes a token produced by :py:func:`dump_payload`.

    :param token: the signed token
    :return: the parsed file, the import context and the group warnings
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
    parsed = ParsedFile(
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
    context = ImportContext(
        badge_types=[BadgeIds(badge_id) for badge_id in data["types"]],
        expiration_date=(
            date.fromisoformat(data["expiration"]) if data["expiration"] else None
        ),
        back_url=data["back"],
        extends=data["extends"],
    )
    return parsed, context, data["warnings"]


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
    """ Name as found in the file."""
    status: GrantorStatus
    """ Outcome of the matching."""
    users: list[User] = field(default_factory=list)
    """ Matching users."""
    count: int = 0
    """ Number of lines of the file with this validator."""

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

    :param names: validator names, one per line of the file (may repeat)
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
    """Returns license numbers of the file which match no user.

    :param rows: lines of the file
    :return: sorted list of unknown license numbers
    """
    licenses = {row.license for row in rows}
    return sorted(licenses - users_by_license(licenses).keys())


@dataclass(frozen=True)
class BadgeTarget:
    """A badge a group may be granted, once checked by :py:func:`resolve_target`."""

    badge_id: BadgeIds
    """ Type of the badge."""
    level: int | None
    """ Level of the badge, if the badge type has levels."""
    activity_id: int | None
    """ Activity of the badge, if any."""


def grantable_activities() -> list[ActivityType]:
    """:return: activities for which the current user may grant badges"""
    if current_user.is_hotline():
        return ActivityType.get_all_types()
    return current_user.get_supervised_activities()


def resolve_target(
    badge_id: BadgeIds,
    activity_id: int | None,
    level: int | None,
    badge_types: list[BadgeIds],
) -> BadgeTarget:
    """Checks that the current user may grant a badge, and completes it.

    Follows the rules of the badge add form: a level specific to an activity
    sets the activity, and badges not accepting activities have none.

    :param badge_id: type of the badge
    :param activity_id: activity of the badge, if any
    :param level: level of the badge, if any
    :param badge_types: badge types which may be granted
    :return: the badge to grant
    :raises BadgeImportError: if the badge is invalid or may not be granted
    """
    if badge_id not in badge_types:
        raise BadgeImportError(f"Badge non autorisé : {badge_id.display_name()}")

    if not badge_id.accepts_activity():
        activity_id = None

    if badge_id.requires_level():
        # Levels of the activity first, as practitioner levels may be renamed per
        # activity. Then any level: a skill level determines its own activity.
        desc = badge_id.levels(activity_id=activity_id).get(
            level
        ) or badge_id.levels().get(level)
        if desc is None:
            raise BadgeImportError("Niveau invalide")
        if desc.activity_id is not None:
            activity_id = desc.activity_id
        elif not desc.accepts_activity:
            activity_id = None
    else:
        level = None

    if badge_id.requires_activity() and activity_id is None:
        raise BadgeImportError("Ce type de badge nécessite une activité")
    if activity_id is not None and activity_id not in {
        activity.id for activity in grantable_activities()
    }:
        raise BadgeImportError("Activité non autorisée")

    return BadgeTarget(badge_id, level, activity_id)


def _find_by_name(name: str, candidates: dict) -> object | None:
    """Finds a candidate by name.

    Names are first compared ignoring case and surrounding spaces, then once
    normalized (see :py:func:`normalize`). Exact comparison comes first as
    normalizing removes symbols: the default practitioner levels, named
    "Niveau" followed by a colored emoji, would all be the same.

    :param name: the name to find
    :param candidates: candidate values by name
    :return: the value of the only candidate with this name, if any
    """
    for compare in (lambda text: text.strip().casefold(), normalize):
        found = [
            value
            for key, value in candidates.items()
            if compare(key) and compare(key) == compare(name)
        ]
        if len(found) == 1:
            return found[0]
    return None


def _suggest_from_text(text: str, badge_types: list[BadgeIds]) -> BadgeTarget | None:
    """Suggests the badge of an extranet group, when a single badge matches it.

    Names are compared once normalized (see :py:func:`normalize`). A skill
    matches if its name is the group. A practitioner level matches if the group
    contains both the name of an activity and the custom name of its level, such
    as "INITIE en ski de randonnée" for a level named "Initié" of "Ski de
    randonnée"; levels keeping their default name never match.

    :param text: a competency group or practitioner level of an extranet export
    :param badge_types: badge types which may be granted
    :return: the suggested badge, or None if none or several match
    """
    key = normalize(text)
    padded_key = f" {key} "
    activities = grantable_activities()
    activity_ids = {activity.id for activity in activities}
    found = set()

    if BadgeIds.Skill in badge_types:
        for level, desc in BadgeIds.Skill.levels().items():
            if normalize(desc.name) == key and (
                desc.activity_id is None or desc.activity_id in activity_ids
            ):
                found.add(BadgeTarget(BadgeIds.Skill, level, desc.activity_id))

    if BadgeIds.Practitioner in badge_types:
        default_names = BadgeIds.Practitioner.levels(only_defaults=True)
        for activity in activities:
            if f" {normalize(activity.name)} " not in padded_key:
                continue
            for level, desc in BadgeIds.Practitioner.levels(
                activity_id=activity.id
            ).items():
                default = default_names.get(level)
                if default is not None and default.name == desc.name:
                    continue
                if f" {normalize(desc.name)} " in padded_key:
                    found.add(BadgeTarget(BadgeIds.Practitioner, level, activity.id))

    return found.pop() if len(found) == 1 else None


@dataclass
class MappingChoice:
    """Badge chosen for a group, before being checked."""

    badge_id: BadgeIds | None = None
    """ Type of the badge, or None to ignore the group."""
    activity_id: int | None = None
    """ Activity of the badge, if any."""
    level: int | None = None
    """ Level of the badge, if any."""


def default_mapping(
    parsed: ParsedFile, default: MappingChoice, badge_types: list[BadgeIds]
) -> list[tuple[MappingChoice, str | None]]:
    """Pre-fills the badge of each group from its lines and the default badge.

    - Extranet groups get the badge suggested from their name, if any, or else
      the default badge.
    - CSV groups get the default badge, with the activity and level of their
      lines when given. An activity or level which cannot be found makes the
      group ignored, rather than silently granting another badge.

    A group whose resulting badge is invalid is ignored, with a warning.

    :param parsed: the parsed file
    :param default: the default badge, from the add form
    :param badge_types: badge types which may be granted
    :return: the choice and an optional warning for each group, in order
    """
    activities = {activity.name: activity.id for activity in grantable_activities()}
    result = []
    for group in parsed.groups():
        hint = parsed.hints.get(group, GroupHint())
        choice = MappingChoice(default.badge_id, default.activity_id, default.level)
        warning = None

        if hint.text:
            suggestion = _suggest_from_text(hint.text, badge_types)
            if suggestion is not None:
                choice = MappingChoice(
                    suggestion.badge_id, suggestion.activity_id, suggestion.level
                )
        if hint.activity:
            choice.activity_id = _find_by_name(hint.activity, activities)
            if choice.activity_id is None:
                warning = f"Activité « {hint.activity} » inconnue ou non autorisée"
        if hint.level and warning is None and choice.badge_id is not None:
            levels = choice.badge_id.levels(activity_id=choice.activity_id)
            names = {desc.name: level for level, desc in levels.items()}
            choice.level = _find_by_name(hint.level, names)
            if choice.level is None:
                warning = f"Niveau « {hint.level} » inconnu"

        if warning is None and choice.badge_id is not None:
            try:
                resolve_target(
                    choice.badge_id, choice.activity_id, choice.level, badge_types
                )
            except BadgeImportError as err:
                if hint.text is None:
                    warning = f"Badge par défaut invalide : {err}"
                else:
                    warning = "Aucun badge reconnu"
        if warning is not None:
            choice.badge_id = None
        result.append((choice, warning))
    return result


def import_badges(
    parsed: ParsedFile,
    mapping: dict[str, BadgeTarget | None],
    context: ImportContext,
) -> BulkImportReport:
    """Creates or renews badges according to the file.

    Badges are granted with :py:func:`collectives.utils.badges.grant_badge`. The
    validator is recorded as grantor when it matches a single user; otherwise the
    importing user is.

    :param parsed: the parsed file
    :param mapping: badge to grant for each group (None to ignore)
    :param context: the import context
    :return: the report of the import
    """
    report = BulkImportReport()
    rows = [row for row in parsed.rows if mapping.get(row.group) is not None]
    report.ignored = len(parsed.rows) - len(rows)

    # For badges with ordered levels, having a level implies having the lower
    # ones: only grant the highest level of each member, badge and activity
    def ordered_key(row: ImportRow) -> tuple | None:
        """Key of rows superseding each other, or None"""
        target = mapping[row.group]
        if target.level is None or not target.badge_id.has_ordered_levels():
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

        expiration_date = context.expiration_date
        if row.attribution_date or expiration_date is None:
            expiration_date = compute_default_expiration_date(
                badge_id=target.badge_id,
                level=target.level,
                attribution_date=row.attribution_date,
            )
        badge = Badge(
            badge_id=target.badge_id,
            level=target.level,
            activity_id=target.activity_id,
            expiration_date=expiration_date,
            creation_time=time.current_time(),
        )

        match = grantors.get(row.grantor)
        try:
            grant_badge(user, badge, report, grantor=match.user if match else None)
        except RuntimeError as err:
            report.errors.append(f"Ligne {row.line} : {user.full_name()} : {err}")

    db.session.commit()
    return report


def _build_form(
    parsed: ParsedFile,
    context: ImportContext,
    defaults: list[MappingChoice],
    **kwargs,
) -> BadgeImportMappingForm:
    """Builds the form to choose the badge of each group.

    :param parsed: the parsed file
    :param context: the import context
    :param defaults: default choice of each group
    :param kwargs: passed to the form constructor
    :return: the form
    """
    activities = sorted(grantable_activities(), key=lambda a: a.name)
    return BadgeImportMappingForm.build(
        parsed.groups(),
        badge_choices=[("", "Ignorer")]
        + [(str(int(b)), b.display_name()) for b in context.badge_types],
        activity_choices=[("", "Pas d'activité")]
        + [(str(a.id), a.name) for a in activities],
        defaults=[
            (
                "" if choice.badge_id is None else str(int(choice.badge_id)),
                "" if choice.activity_id is None else str(choice.activity_id),
                "" if choice.level is None else str(choice.level),
            )
            for choice in defaults
        ],
        **kwargs,
    )


def _render_mapping(
    form: BadgeImportMappingForm,
    parsed: ParsedFile,
    context: ImportContext,
    warnings: list,
    group_errors: dict | None = None,
):
    """Renders the page to choose the badge of each group of a file, along with
    diagnostics about the file.

    :param form: the mapping form
    :param parsed: the parsed file
    :param context: the import context
    :param warnings: warning of each group, from :py:func:`default_mapping`
    :param group_errors: error of each group, by index, after a submission
    """
    grantors = match_grantors(row.grantor for row in parsed.rows)
    status_order = list(GrantorStatus)
    grantors = sorted(
        grantors.values(),
        key=lambda match: (status_order.index(match.status), -match.count, match.name),
    )
    return render_template(
        "activity_supervision/badge_import.html",
        title="Import d'un fichier de badges",
        form=form,
        parsed=parsed,
        context=context,
        warnings=warnings,
        group_errors=group_errors or {},
        group_counts=parsed.group_counts(),
        grantors=grantors,
        grantor_status=GrantorStatus,
        unknown_licenses=unknown_licenses(parsed.rows),
        confirm_url=url_for(f"{request.blueprint}.confirm_badge_import"),
        badge_ids=[int(badge_id) for badge_id in context.badge_types],
        accepts_activity={
            int(badge_id): badge_id.accepts_activity()
            for badge_id in context.badge_types
        },
        activity_ids=[activity.id for activity in ActivityType.get_all_types()],
    )


def start_import(file_storage, default: MappingChoice, context: ImportContext):
    """Parses an uploaded file, and displays the page to choose the badge of
    each of its groups.

    :param file_storage: the uploaded file
    :param default: the default badge, from the add form
    :param context: the import context
    :return: the response
    """
    try:
        parsed = parse_file(file_storage)
    except BadgeImportError as err:
        flash(str(err), "error")
        return redirect(context.back_url)

    mapping = default_mapping(parsed, default, context.badge_types)
    warnings = [warning for _, warning in mapping]
    form = _build_form(
        parsed, context, [choice for choice, _ in mapping], formdata=None
    )
    form.payload.data = dump_payload(parsed, context, warnings)
    return _render_mapping(form, parsed, context, warnings)


def confirm_import():
    """Imports the badges of a file, once the user has chosen the badge of each
    group. Displays the mapping page again if a choice is invalid.

    :return: the response
    """
    try:
        parsed, context, warnings = load_payload(request.form.get("payload", ""))
    except BadgeImportError as err:
        flash(str(err), "error")
        return redirect(url_for("event.index"))

    form = _build_form(parsed, context, [MappingChoice() for _ in parsed.groups()])
    if not form.validate_on_submit():
        return _render_mapping(form, parsed, context, warnings)

    mapping = {}
    group_errors = {}
    for i, (group, badge_field, activity_field, level_field) in enumerate(
        form.group_fields()
    ):
        if not badge_field.data:
            mapping[group] = None
            continue
        try:
            mapping[group] = resolve_target(
                BadgeIds(int(badge_field.data)),
                int(activity_field.data) if activity_field.data else None,
                int(level_field.data) if level_field.data else None,
                context.badge_types,
            )
        except (BadgeImportError, ValueError) as err:
            group_errors[i] = str(err)

    if group_errors:
        return _render_mapping(form, parsed, context, warnings, group_errors)
    if not any(mapping.values()):
        flash("Aucun badge sélectionné : rien n'a été importé.", "warning")
        return _render_mapping(form, parsed, context, warnings)

    report = import_badges(parsed, mapping, context)
    return render_template(
        "activity_supervision/badge_import.html",
        title="Import d'un fichier de badges",
        report=report,
        context=context,
    )
