"""Module for base functions of badge management"""

import codecs
import csv
from datetime import datetime
from typing import List, Sequence, Union

from flask import flash, render_template, request, send_file
from flask_login import current_user
from markupsafe import Markup

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.forms.badge import AddBadgeForm, compute_default_expiration_date
from collectives.models import (
    ActivityType,
    Badge,
    BadgeCustomLevel,
    BadgeIds,
    Configuration,
    User,
    db,
)
from collectives.models.badge import BadgeIds
from collectives.utils import export, time
from collectives.utils.misc import sanitize_file_name


def export_badge(badge_types: Sequence[BadgeIds] | None = None):
    """Create an Excel document with the contact information of users with badge.

    :param type: The type of badge to export
    :return: The Excel file with the roles.
    """
    form = ActivityTypeSelectionForm(
        all_enabled=True,
    )

    if not form.validate_on_submit():
        return False

    if form.activity_id.data != ActivityTypeSelectionForm.ALL_ACTIVITIES:
        activity_type = db.session.get(ActivityType, form.activity_id.data)
        if not current_user.is_hotline():
            if activity_type not in current_user.get_supervised_activities():
                return False
    else:
        if current_user.is_hotline():
            activity_type = ActivityType.query.all()
        else:
            activity_type = current_user.get_supervised_activities()

    query = Badge.query
    # we remove role not linked anymore to a user
    query = query.filter(Badge.user.has(User.id))
    if activity_type is not None:
        if isinstance(activity_type, list):
            query = query.filter(Badge.activity_id.in_([t.id for t in activity_type]))
        else:
            query = query.filter(Badge.activity_id == activity_type.id)

    if badge_types is not None:
        query = query.filter(Badge.badge_id.in_(badge_types))

    badges = query.all()

    if not isinstance(activity_type, list):
        filename = activity_type.name
    else:
        filename = ""

    out = export.export_badges(badges)

    club_name = sanitize_file_name(Configuration.CLUB_NAME)

    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"{club_name} - Export {type_title(badge_types)} {filename}.xlsx",
        as_attachment=True,
    )


# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
def list_page(
    routes: dict,
    badge_types: Union[BadgeIds, List[BadgeIds]] = None,
    auto_date: bool = False,
    level: bool = False,
    show_grantor: bool = False,
    extends: str = "activity_supervision/activity_supervision.html",
    allow_add: bool = True,
    title: str | None = None,
):
    """Route for activity supervisors to access badges list and management form.

    :param type: The type(s) of badge to export
    :param auto_date: if True, Badges are added to the end of the federal year. Else
        activity supervisor can choose.
    :param level: if True, display level setting
    :param extends: path to the template which extends the page
    :param routes: Lists of urls of others endpoint. This dict should have these keys:
                ``add``, ``export``, ``delete``, ``renew``,.
    :param allow_add: Whether to allow adding new badges
    :param title: Title of the page. If None, computed from badge_types
    """

    # convert to list
    if isinstance(badge_types, BadgeIds):
        badge_types = [
            badge_types,
        ]
    elif badge_types is None:
        badge_types = []

    if allow_add:
        add_badge_form = AddBadgeForm(
            badge_ids=badge_types, badge_type=type_title(badge_types)
        )

        if len(badge_types) == 1:
            del add_badge_form.badge_id
        if auto_date:
            del add_badge_form.expiration_date
        if not level:
            del add_badge_form.level
    else:
        add_badge_form = None

    export_form = ActivityTypeSelectionForm(
        submit_label="Générer Excel",
        activity_list=current_user.get_supervised_activities(),
        all_enabled=True,
    )

    activity_ids = [activity.id for activity in ActivityType.get_all_types()]

    return render_template(
        "activity_supervision/badges_list.html",
        add_badge_form=add_badge_form,
        export_form=export_form,
        title=title or type_title(badge_types),
        badge_ids=[badge_id.value for badge_id in badge_types],
        auto_date=auto_date,
        level=level,
        show_grantor=show_grantor,
        extends=extends,
        routes=routes,
        activity_ids=activity_ids,
    )


def validate_user_badge(
    user: User,
    badge: Badge,
    verbose: bool = True,
) -> Badge:
    """Validates that the badge can be assigned to the user, possibly updating an existing badge.

    Returns the badge to add (which may be an existing badge updated), or raises RuntimeError.
    """
    if badge.badge_id.requires_activity():
        if not badge.activity_id:
            raise RuntimeError("Ce badge doit être associé à une activité")

    if badge.badge_id.requires_level():
        level_desc = badge.badge_id.levels().get(badge.level)
        if level_desc is None:
            raise RuntimeError("Niveau de badge invalide")
        if not level_desc.is_compatible_with_activity(badge.activity_id):
            raise RuntimeError(
                "Niveau de badge incompatible avec l'activité sélectionnée"
            )
        if level_desc.activity_id is not None:
            badge.activity_id = level_desc.activity_id

    matching_badges = [
        bdg
        for bdg in user.matching_badges(
            badge_ids=(badge.badge_id,),
            level=None if badge.badge_id.has_ordered_levels() else badge.level,
        )
        if bdg.activity_id == badge.activity_id
    ]

    for existing in matching_badges:
        if (
            badge.expiration_date
            and (
                existing.expiration_date is None
                or existing.expiration_date > badge.expiration_date
            )
            and (not badge.badge_id.requires_level() or existing.level == badge.level)
        ):
            raise RuntimeError(
                "L'utilisateur a déjà ce badge pour cette activité"
                " avec une date d'expiration postérieure",
            )

        if (
            badge.badge_id.has_ordered_levels()
            and existing.level
            and (badge.level is None or existing.level > badge.level)
        ):
            raise RuntimeError(
                "L'utilisateur a déjà ce badge pour cette activité"
                " avec un niveau supérieur",
            )

        # Renew existing badge
        existing.expiration_date = badge.expiration_date
        existing.level = badge.level
        if verbose:
            flash(
                "L'utilisateur a déjà ce badge pour cette activité,"
                " la date d'expiration et/ou le niveau ont été mise à jour.",
                "info",
            )

        return existing

    return badge


def add_badge(
    badge_types: list[BadgeIds] = None, auto_date: bool = False, level: bool = False
) -> None:
    """Route for an activity supervisor to add or renew a Badge to a user.

    :param type: The type of badge to add"""

    if isinstance(badge_types, BadgeIds):
        badge_types = [
            badge_types,
        ]

    add_badge_form = AddBadgeForm(badge_ids=badge_types)

    if badge_types is not None and len(badge_types) == 1:
        add_badge_form.badge_id.data = badge_types[0]

    if auto_date:
        del add_badge_form.expiration_date
    if not level:
        del add_badge_form.level

    if not add_badge_form.validate_on_submit():
        form_errors = "".join(
            f"<li> {add_badge_form[field].label.text}: {', '.join(errors)} </li>"
            for field, errors in add_badge_form.errors.items()
        )

        flash(
            Markup(
                f"Erreur lors de l'ajout du badge {type_title(badge_types)}: <ul> {form_errors} </ul>"
            ),
            "error",
        )
        return

    badge = Badge(creation_time=time.current_time())
    add_badge_form.populate_obj(badge)
    badge.activity_id = badge.activity_id or None

    if auto_date:
        badge.expiration_date = compute_default_expiration_date(
            badge_id=badge.badge_id, level=badge.level
        )

    csv_file = add_badge_form.csv_file.data
    if csv_file:
        # Process the CSV file
        try:
            add_bulk(csv_file, badge_prototype=badge)
        except RuntimeError as err:
            flash(Markup(str(err)), "error")
        return

    # else add badge for a single user
    user: User = db.session.get(User, badge.user_id)
    if user is None:
        flash("Utilisateur invalide", "error")
        return

    try:
        badge = validate_user_badge(user, badge)
        badge.grantor_id = current_user.id
        db.session.add(badge)
        db.session.commit()
    except RuntimeError as err:
        flash(str(err), "error")


def add_bulk(file_storage, badge_prototype: Badge) -> None:
    """Process a CSV file containing lines (license, attribution_date) and assign badge.

    The CSV may have a header. Date formats accepted: YYYY-MM-DD or DD/MM/YYYY.
    """

    # Read a sample from the uploaded stream to detect encoding and delimiter.
    file_storage.stream.seek(0)
    sample = file_storage.stream.read(8192) or b""

    # Try to decode sample as utf-8, fallback to iso-8859-1
    encoding = "utf8"
    try:
        sample_text = sample.decode(encoding)
    except Exception:
        encoding = "iso-8859-1"
        sample_text = sample.decode(encoding, errors="replace")

    # Try to detect delimiter with csv.Sniffer (prefer ; or ,). Fallback to simple heuristic.
    try:
        dialect = csv.Sniffer().sniff(sample_text, delimiters=";,")
        delimiter = dialect.delimiter
    except Exception:
        delimiter = ";" if sample_text.count(";") > sample_text.count(",") else ","

    # Reset stream and create a text iterator with the chosen encoding, then csv reader with detected delimiter.
    file_storage.stream.seek(0)
    stream = codecs.iterdecode(file_storage.stream, encoding)
    reader = csv.reader(stream, delimiter=delimiter)

    created = 0
    updated = 0
    failed = []

    # Read all rows
    rows = list(reader)
    if not rows:
        raise RuntimeError("Fichier vide.")

    # detect header if first row contains 'license' text or non-numeric license
    start_index = 0
    first = rows[0]
    if any(h and h.lower() in ("license", "licence") for h in first) or (
        first and not first[0].strip().isdigit()
    ):
        start_index = 1
    header_map = None
    if start_index == 1:
        # build a header -> index map for named column matching (case-insensitive)
        header = [h.strip().lower() if h else "" for h in first]
        header_map = {h: i for i, h in enumerate(header) if h}

    def _col_index(names, default_idx):
        """Return the column index for the first matching name in names using header_map, or default_idx."""
        if header_map:
            for n in names:
                if n in header_map:
                    return header_map[n]
            return None
        return default_idx

    def _col_value(row, idx):
        """Return the column value for the first matching name in names using header_map, or default_idx."""
        if idx is not None and idx < len(row):
            return row[idx].strip()
        return None

    activity_names = {a.name: a.id for a in current_user.get_supervised_activities()}

    license_index = _col_index(["license", "licence"], 0)
    date_index = _col_index(["attribution_date", "date"], 1)
    activity_index = _col_index(["activity", "activite"], 2)
    level_index = _col_index(["level", "niveau"], 3)

    for row in rows[start_index:]:
        if not row:
            continue

        license_val = _col_value(row, license_index)
        date_str = _col_value(row, date_index)
        activity_name = _col_value(row, activity_index)
        level_name = _col_value(row, level_index)

        if not license_val:
            continue

        user = User.query.filter_by(license=license_val).first()
        if user is None:
            failed.append(f"Utilisateur introuvable: {license_val}")
            continue

        user_identifier = f"{user.full_name()} (licence {user.license})"

        # resolve activity by name if provided
        activity_id = badge_prototype.activity_id
        if activity_name:
            activity_id = activity_names.get(activity_name)
            if activity_id is None:
                failed.append(
                    f"Activité introuvable pour {user_identifier}: {activity_name}"
                )
                continue

        # resolve level name -> level id (practitioner default levels or custom skill levels)
        level = badge_prototype.level
        if level_name:
            levels = badge_prototype.badge_id.levels(activity_id=activity_id)
            level_names = {desc.name: lvl for lvl, desc in levels.items()}

            level = level_names.get(level_name)
            if level is None:
                failed.append(f"Niveau invalide pour {user_identifier}: {level_name}")
                continue

        # parse date
        expiration_date = badge_prototype.expiration_date
        if date_str:
            parsed = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    parsed = datetime.strptime(date_str, fmt).date()
                    break
                except Exception:
                    parsed = None
            if parsed is None:
                failed.append(f"Date invalide pour {user_identifier}: {date_str}")
                continue
            expiration_date = compute_default_expiration_date(
                badge_id=badge_prototype.badge_id,
                level=level,
                attribution_date=parsed,
            )
        elif expiration_date is None:
            expiration_date = compute_default_expiration_date(
                badge_id=badge_prototype.badge_id,
                level=level,
            )

        tentative_badge = Badge(
            user_id=user.id,
            badge_id=badge_prototype.badge_id,
            activity_id=activity_id,
            level=level,
            expiration_date=expiration_date,
            creation_time=time.current_time(),
        )

        try:
            resolved_badge = validate_user_badge(user, tentative_badge, verbose=False)
        except RuntimeError as err:
            failed.append(f"{user_identifier}: {err}")
            continue

        resolved_badge.grantor_id = current_user.id
        db.session.add(resolved_badge)
        try:
            db.session.commit()
            if resolved_badge.id == tentative_badge.id:
                created += 1
            else:
                updated += 1
        except Exception:
            db.session.rollback()
            failed.append(f"Erreur en mettant à jour {license_val}")

    # summarize results
    if failed:
        flash(
            f"Import terminé: {created} créés, {updated} mis à jour. Erreurs: "
            + "; ".join(failed),
            "warning",
        )
    else:
        flash(f"Import terminé: {created} créés, {updated} mis à jour.", "success")


def renew_badge(
    badge_id: int,
    badge_type: BadgeIds = None,
) -> None:
    """Route for an activity supervisor to add or renew a Badge to a user.

    :param type: The type of badge to renew"""
    badge: Badge = db.session.get(Badge, badge_id)

    if not has_rights_to_modify_badge(badge, badge_type):
        flash("Badge invalide", "error")
        return None

    if badge.expiration_date is None:
        flash("Badge non renouvelable", "warning")
        return None

    badge.expiration_date = compute_default_expiration_date(badge.badge_id, badge.level)
    badge.grantor_id = current_user.id
    db.session.add(badge)
    db.session.commit()
    return None


def delete_badge(badge_id: int, badge_type: BadgeIds = None) -> None:
    """Delete an user badge, while performing basic checks.

    :param badge_id: Id of badge to delete
    :param type: Refuse to delete if not the right type. None for no check
    """

    badge = db.session.get(Badge, badge_id)

    if not has_rights_to_modify_badge(badge, badge_type):
        flash("Badge invalide", "error")
        return None

    db.session.delete(badge)
    db.session.commit()
    return None


def type_title(badge_type: Union[BadgeIds, List[BadgeIds]]) -> str:
    """Returns a title regard the type of badge.

    :param type: The type of badge to export
    """
    if isinstance(badge_type, BadgeIds):
        return badge_type.display_name()
    if badge_type and len(badge_type) <= 3:
        return ", ".join([bdg.display_name() for bdg in badge_type])
    return "Badge"


def has_rights_to_modify_badge(badge: Badge, badge_type: BadgeIds) -> bool:
    """Checks if current user has sufficient right to modify this badge."""
    if badge is None:
        return False

    if badge_type is not None and badge_type != badge.badge_id:
        return False

    if badge.activity_type is not None:
        if badge.activity_type not in current_user.get_supervised_activities():
            if not current_user.is_hotline():
                return False

    return True
