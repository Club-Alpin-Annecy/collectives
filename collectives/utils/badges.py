"""Module for base functions of badge management"""

from typing import List, Sequence, Union

from flask import flash, render_template, send_file, request
from flask_login import current_user

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.forms.badge import AddBadgeForm, compute_default_expiration_date
from collectives.models import (
    ActivityType,
    Badge,
    BadgeIds,
    Configuration,
    User,
    db,
    BadgeCustomLevel,
)
from collectives.utils import export, time
from collectives.utils.misc import sanitize_file_name
from markupsafe import Markup

import csv
import codecs
from datetime import datetime

from collectives.models import User, db
from collectives.models.badge import BadgeIds
from collectives.forms.badge import compute_default_expiration_date


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
):
    
    if badge.badge_id.requires_activity():
        if not badge.activity_id:
            raise RuntimeError(
                "Ce badge doit être associé à une activité"
            )
    badge.activity_id = badge.activity_id or None

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

    if len(badge_types) == 1:
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

    if auto_date:
        badge.expiration_date = compute_default_expiration_date(
            badge_id=badge.badge_id, level=badge.level
        )

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


def add_bulk(badge_type: BadgeIds = None, auto_date: bool = False, level: int = None):
    """Process a CSV file containing lines (license, attribution_date) and assign badge.

    The CSV may have a header. Date formats accepted: YYYY-MM-DD or DD/MM/YYYY.
    """

    file_storage = request.files.get("csv_file")
    if file_storage is None or file_storage.filename == "":
        raise RuntimeError("Aucun fichier fourni.")

    # Try to decode as utf-8, fallback to iso-8859-1
    try:
        stream = codecs.iterdecode(file_storage.stream, "utf8")
        reader = csv.reader(stream)
    except Exception:
        file_storage.stream.seek(0)
        stream = codecs.iterdecode(file_storage.stream, "iso-8859-1")
        reader = csv.reader(stream)

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
    if any(
        h and h.lower() in ("license", "licence", "licence_number", "id") for h in first
    ) or (first and not first[0].strip().isdigit()):
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
        return default_idx

    # default badge type provided by the form (required to interpret rows)
    default_badge_id = request.form.get("default_badge_id")
    try:
        default_badge = BadgeIds(int(default_badge_id)) if default_badge_id else None
    except Exception:
        default_badge = None

    for row in rows[start_index:]:
        if not row:
            continue

        license_val = row[0].strip() if len(row) > 0 else ""
        date_str = row[1].strip() if len(row) > 1 else ""
        activity_name = row[2].strip() if len(row) > 2 else ""
        level_name = row[3].strip() if len(row) > 3 else ""

        if not license_val:
            continue

        user = User.query.filter_by(license=license_val).first()
        if user is None:
            failed.append(f"Utilisateur introuvable: {license_val}")
            continue

        # parse date
        expiration_date = None
        if date_str:
            parsed = None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    parsed = datetime.strptime(date_str, fmt).date()
                    break
                except Exception:
                    parsed = None
            if parsed is None:
                failed.append(f"Date invalide pour {license_val}: {date_str}")
                continue
            expiration_date = parsed
        else:
            expiration_date = compute_default_expiration_date()

        # badge type comes from form default (required)
        badge_type = default_badge or BadgeIds.Benevole

        # resolve activity by name if provided
        activity_id = None
        if activity_name:
            activity = ActivityType.query.filter_by(name=activity_name).first()
            if activity is None:
                failed.append(
                    f"Activité introuvable pour {license_val}: {activity_name}"
                )
                continue
            activity_id = activity.id

        # resolve level name -> level id (practitioner default levels or custom skill levels)
        level = None
        if level_name:
            if badge_type == BadgeIds.Practitioner:
                levels = badge_type.levels(activity_id=activity_id)
                match = None
                for lvl_key, desc in levels.items():
                    if (
                        desc.name == level_name
                        or getattr(desc, "abbrev", None) == level_name
                        or level_name in desc.name
                    ):
                        match = lvl_key
                        break
                if match is None:
                    failed.append(f"Niveau invalide pour {license_val}: {level_name}")
                    continue
                level = match
            elif badge_type == BadgeIds.Skill:
                candidates = BadgeCustomLevel.get_all(
                    badge_id=BadgeIds.Skill, include_deprecated=False
                )
                match = None
                for cand in candidates:
                    if (
                        cand.name == level_name
                        or cand.abbrev == level_name
                        or level_name in cand.name
                    ):
                        match = cand.id
                        break
                if match is None:
                    failed.append(
                        f"Niveau de compétence introuvable pour {license_val}: {level_name}"
                    )
                    continue
                level = match

        # check for existing matching badges for this badge_type and activity
        matching = [
            b
            for b in user.matching_badges({badge_type}, valid_only=False)
            if b.activity_id == activity_id
        ]
        if matching:
            existing = matching[0]
            if expiration_date and (
                existing.expiration_date is None
                or existing.expiration_date > expiration_date
            ):
                failed.append(
                    f"{license_val}: badge existant avec une date d'expiration ultérieure"
                )
                continue
            existing.expiration_date = expiration_date
            if level is not None:
                existing.level = level
            existing.grantor_id = current_user.id
            db.session.add(existing)
            try:
                db.session.commit()
                updated += 1
            except Exception:
                db.session.rollback()
                failed.append(f"Erreur en mettant à jour {license_val}")
        else:
            try:
                user.assign_badge(
                    badge_type,
                    expiration_date=expiration_date,
                    activity_id=activity_id,
                    level=level,
                    grantor_id=current_user.id,
                )
                created += 1
            except Exception:
                failed.append(f"Erreur lors de l'ajout du badge pour {license_val}")

    # summarize results
    if failed:
        flash(
            f"Import terminé: {created} créés, {updated} mis à jour. Erreurs: "
            + "; ".join(failed),
            "warning",
        )
    else:
        flash(f"Import terminé: {created} créés, {updated} mis à jour.", "success")

    # return redirect(url_for(".volunteers_list"))


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
