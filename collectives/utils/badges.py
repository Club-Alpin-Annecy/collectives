"""Module for base functions of badge management"""

from typing import List, Sequence, Union

from flask import flash, render_template, send_file
from flask_login import current_user

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.forms.badge import AddBadgeForm, compute_default_expiration_date
from collectives.models import ActivityType, Badge, BadgeIds, Configuration, User, db
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
        add_badge_form = AddBadgeForm(badge_type=type_title(badge_types))

        if badge_types:
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


def add_badge(
    badge_type: BadgeIds = None, auto_date: bool = False, level: bool = False
) -> None:
    """Route for an activity supervisor to add or renew a Badge to a user.

    :param type: The type of badge to add"""

    add_badge_form = AddBadgeForm()
    if badge_type:
        del add_badge_form.badge_id
    if auto_date:
        del add_badge_form.expiration_date
    if not level:
        del add_badge_form.level

    if not add_badge_form.validate_on_submit():
        flash(f"Erreur lors de l'ajout du statut {type_title(badge_type)}", "error")
        return None

    badge = Badge(creation_time=time.current_time())
    add_badge_form.populate_obj(badge)

    if badge_type:
        badge.badge_id = badge_type
    if auto_date:
        badge.expiration_date = compute_default_expiration_date(
            badge_id=badge.badge_id, level=badge.level
        )

    user: User = db.session.get(User, badge.user_id)
    if user is None:
        flash("Utilisateur invalide", "error")
        return None

    matching_badges = [
        bdg
        for bdg in user.matching_badges(badge_ids=(badge.badge_id,))
        if bdg.activity_id == badge.activity_id
    ]

    if matching_badges:
        existing = matching_badges[0]
        if badge.expiration_date and (
            existing.expiration_date is None
            or existing.expiration_date > badge.expiration_date
        ):
            flash(
                "L'utilisateur a déjà ce badge pour cette activité"
                " avec une date d'expiration postérieure",
                "error",
            )
            return None

        if existing.level and (badge.level is None or existing.level > badge.level):
            flash(
                "L'utilisateur a déjà ce badge pour cette activité"
                " avec un niveau supérieur",
                "error",
            )
            return None

        # Renew existing badge
        existing.expiration_date = badge.expiration_date
        existing.level = badge.level
        badge = existing
        flash(
            "L'utilisateur a déjà ce badge pour cette activité,"
            " la date d'expiration a été mise à jour.",
            "info",
        )

    badge.grantor_id = current_user.id
    db.session.add(badge)
    db.session.commit()

    return None


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
